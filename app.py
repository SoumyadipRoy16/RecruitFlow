import logging
from click import prompt
import streamlit as st
import json
import os
import time
from pathlib import Path
import pandas as pd
from utils.config import Config
from utils.database import DatabaseManager
from utils.pdf_processor import PDFProcessor
from utils.agents import JobDescriptionSummarizer, RecruitingAgent, InterviewScheduler

logger = logging.getLogger(__name__)


# Initialize configuration and database
Config.validate()
db = DatabaseManager()

# Set page config
st.set_page_config(
    page_title="RecruitFlow",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
        .main {
            background-color: #f5f5f5;
        }
        .sidebar .sidebar-content {
            background-color: #2c3e50;
            color: white;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .stButton>button {
            background-color: #3498db;
            color: white;
            border-radius: 5px;
            padding: 0.5rem 1rem;
        }
        .stTextInput>div>div>input, .stTextArea>div>div>textarea {
            border-radius: 5px;
        }
        .match-high {
            background-color: #d4edda !important;
        }
        .match-medium {
            background-color: #fff3cd !important;
        }
        .match-low {
            background-color: #f8d7da !important;
        }
        .card {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            padding: 1.5rem;
            margin-bottom: 1rem;
            background-color: white;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'jobs_loaded' not in st.session_state:
    st.session_state.jobs_loaded = False
if 'candidates_processed' not in st.session_state:
    st.session_state.candidates_processed = False

# Helper functions
def load_jobs_from_file():
    """Load jobs from JSON file into database"""
    try:
        with open(Config.JOBS_FILE, 'r') as f:
            jobs = json.load(f)
            
        summarizer = JobDescriptionSummarizer()
        for job in jobs:
            existing_job = db.get_jobs()
            if not any(j['title'] == job['title'] for j in existing_job):
                summary = summarizer.summarize_job_description(job['description'])
                db.add_job(job['title'], job['description'], json.dumps(summary) if summary else None)
        
        st.session_state.jobs_loaded = True
        st.success(f"Loaded {len(jobs)} jobs into database!")
    except Exception as e:
        st.error(f"Error loading jobs: {e}")

def process_candidate_cvs():
    """Process all CVs in the CVs folder"""
    try:
        cvs_folder = Path(Config.CVS_FOLDER)
        pdf_files = list(cvs_folder.glob("*.pdf"))
        
        if not pdf_files:
            st.warning("No PDF files found in the CVs folder!")
            return
        
        processor = PDFProcessor()
        recruiting_agent = RecruitingAgent()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, pdf_path in enumerate(pdf_files):
            status_text.text(f"Processing {i+1}/{len(pdf_files)}: {pdf_path.name}")
            progress_bar.progress((i + 1) / len(pdf_files))
            
            # Check if candidate already exists
            existing_candidates = db.get_candidates()
            if any(c['cv_path'] == str(pdf_path) for c in existing_candidates):
                continue
            
            # Process CV
            cv_text = processor.extract_text_from_pdf(str(pdf_path))
            basic_info = processor.extract_candidate_info(cv_text)
            extracted_data = recruiting_agent.extract_candidate_data(cv_text)
            
            # Store in database
            db.add_candidate(
                name=basic_info.get('name', pdf_path.stem),
                email=basic_info.get('email'),
                phone=basic_info.get('phone'),
                cv_path=str(pdf_path),
                extracted_data=json.dumps(extracted_data) if extracted_data else None
            )
        
        st.session_state.candidates_processed = True
        status_text.text(f"Processed {len(pdf_files)} CVs successfully!")
    except Exception as e:
        st.error(f"Error processing CVs: {e}")

def match_candidates_to_jobs():
    """Match all candidates to all jobs"""
    try:
        jobs = db.get_jobs()
        candidates = db.get_candidates()
        
        if not jobs or not candidates:
            st.warning("No jobs or candidates to match!")
            return
        
        recruiting_agent = RecruitingAgent()
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_matches = len(jobs) * len(candidates)
        processed = 0
        
        for job in jobs:
            job_summary = json.loads(job['summary']) if job['summary'] else None
            if not job_summary:
                continue
                
            for candidate in candidates:
                status_text.text(f"Matching candidates... {processed}/{total_matches}")
                progress_bar.progress(processed / total_matches)
                processed += 1
                
                # Check if match already exists
                existing_matches = db.get_matches(job_id=job['id'], candidate_id=candidate['id'])
                if existing_matches:
                    continue
                
                # Calculate match score
                candidate_data = json.loads(candidate['extracted_data']) if candidate['extracted_data'] else None
                if not candidate_data:
                    continue
                
                match_result = recruiting_agent.calculate_match_score(job_summary, candidate_data)
                if match_result and 'match_score' in match_result:
                    db.add_match(job['id'], candidate['id'], match_result['match_score'])
        
        status_text.text("Matching completed successfully!")
    except Exception as e:
        st.error(f"Error matching candidates to jobs: {e}")

def get_match_class(match_score: float) -> str:
    """Get CSS class based on match score"""
    if match_score >= 80:
        return "match-high"
    elif match_score >= 50:
        return "match-medium"
    else:
        return "match-low"

# Sidebar navigation
st.sidebar.title("RecruitFlow")
menu_options = [
    "Dashboard",
    "Job Descriptions",
    "Candidate CVs",
    "Matching Results",
    "Interview Scheduling"
]
selected_page = st.sidebar.radio("Navigation", menu_options)

# Main content
if selected_page == "Dashboard":
    st.title("📊 Dashboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Jobs", len(db.get_jobs()))
    with col2:
        st.metric("Total Candidates", len(db.get_candidates()))
    with col3:
        st.metric("Total Matches", len(db.get_matches()))
    
    st.markdown("---")
    
    # Data loading section
    st.subheader("Data Initialization")
    if not st.session_state.jobs_loaded:
        if st.button("Load Jobs from JSON"):
            load_jobs_from_file()
    else:
        st.success("Jobs already loaded into database!")
    
    if not st.session_state.candidates_processed:
        if st.button("Process Candidate CVs"):
            process_candidate_cvs()
    else:
        st.success("Candidates already processed!")
    
    if st.session_state.jobs_loaded and st.session_state.candidates_processed:
        if st.button("Run Candidate Matching"):
            match_candidates_to_jobs()
    
    st.markdown("---")
    
    # Recent activity
    st.subheader("Recent Activity")
    recent_matches = db.get_matches()[:5]
    if recent_matches:
        for match in recent_matches:
            with st.container():
                st.markdown(f"""
                <div class="card {get_match_class(match['match_score'])}">
                    <h4>{match.get('job_title', 'Job')} ↔ {match.get('candidate_name', 'Candidate')}</h4>
                    <p><strong>Match Score:</strong> {match['match_score']:.1f}%</p>
                    <p><strong>Date:</strong> {match['created_at']}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No recent matches found")

elif selected_page == "Job Descriptions":
    st.title("📝 Job Descriptions")
    
    # Add new job
    with st.expander("Add New Job Description"):
        with st.form("add_job_form"):
            title = st.text_input("Job Title")
            description = st.text_area("Job Description", height=300)
            
            if st.form_submit_button("Add Job"):
                if title and description:
                    summarizer = JobDescriptionSummarizer()
                    summary = summarizer.summarize_job_description(description)
                    job_id = db.add_job(title, description, json.dumps(summary) if summary else None)
                    if job_id:
                        st.success("Job added successfully!")
                    else:
                        st.error("Error adding job")
                else:
                    st.warning("Please provide both title and description")
    
    # View jobs
    st.subheader("Available Jobs")
    jobs = db.get_jobs()
    if jobs:
        selected_job_id = st.selectbox(
            "Select a job to view details",
            options=[job['id'] for job in jobs],
            format_func=lambda x: next(job['title'] for job in jobs if job['id'] == x)
        )
        
        selected_job = next(job for job in jobs if job['id'] == selected_job_id)
        
        st.markdown(f"### {selected_job['title']}")
        st.markdown("#### Description")
        st.write(selected_job['description'])
        
        if selected_job['summary']:
            st.markdown("#### AI Summary")
            summary = json.loads(selected_job['summary'])
            st.json(summary)
    else:
        st.info("No jobs available. Add some jobs first.")

elif selected_page == "Candidate CVs":
    st.title("📄 Candidate CVs")
    
    # Upload new CV
    with st.expander("Upload New CV"):
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        if uploaded_file is not None:
            # Save to CVs folder
            cvs_folder = Path(Config.CVS_FOLDER)
            cvs_folder.mkdir(parents=True, exist_ok=True)
            
            file_path = cvs_folder / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Process CV
            processor = PDFProcessor()
            recruiting_agent = RecruitingAgent()
            
            cv_text = processor.extract_text_from_pdf(str(file_path))
            basic_info = processor.extract_candidate_info(cv_text)
            extracted_data = recruiting_agent.extract_candidate_data(cv_text)
            
            # Add to database
            db.add_candidate(
                name=basic_info.get('name', file_path.stem),
                email=basic_info.get('email'),
                phone=basic_info.get('phone'),
                cv_path=str(file_path),
                extracted_data=json.dumps(extracted_data) if extracted_data else None
            )
            
            st.success("CV processed and added to database!")
    
    # View candidates
    st.subheader("Candidate Profiles")
    candidates = db.get_candidates()
    if candidates:
        selected_candidate_id = st.selectbox(
            "Select a candidate to view details",
            options=[candidate['id'] for candidate in candidates],
            format_func=lambda x: next(candidate['name'] for candidate in candidates if candidate['id'] == x)
        )
        
        selected_candidate = next(candidate for candidate in candidates if candidate['id'] == selected_candidate_id)
        
        st.markdown(f"### {selected_candidate['name']}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Contact Info")
            st.write(f"Email: {selected_candidate['email'] or 'Not available'}")
            st.write(f"Phone: {selected_candidate['phone'] or 'Not available'}")
            st.write(f"CV Path: {selected_candidate['cv_path']}")
        
        with col2:
            if selected_candidate['extracted_data']:
                st.markdown("#### Extracted Data")
                st.json(json.loads(selected_candidate['extracted_data']))
            else:
                st.warning("No extracted data available for this candidate")
    else:
        st.info("No candidates available. Upload some CVs first.")

elif selected_page == "Matching Results":
    st.title("🔍 Matching Results")
    
    jobs = db.get_jobs()
    candidates = db.get_candidates()
    
    if not jobs or not candidates:
        st.warning("You need both jobs and candidates to see matching results!")
    else:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            selected_job_id = st.selectbox(
                "Filter by Job",
                options=[None] + [job['id'] for job in jobs],
                format_func=lambda x: next(job['title'] for job in jobs if job['id'] == x) if x else "All Jobs"
            )
        with col2:
            min_score = st.slider("Minimum Match Score", 0, 100, 50)
        
        # Get matches
        if selected_job_id:
            matches = db.get_matches(job_id=selected_job_id)
            job_title = next(job['title'] for job in jobs if job['id'] == selected_job_id)
            st.subheader(f"Matching Candidates for: {job_title}")
        else:
            matches = db.get_matches()
            st.subheader("All Job-Candidate Matches")
        
        # Filter by score
        matches = [m for m in matches if m['match_score'] >= min_score]
        
        if matches:
            # Display as table
            df = pd.DataFrame(matches)
            if 'job_title' in df.columns:
                df = df[['job_title', 'candidate_name', 'match_score', 'is_shortlisted', 'interview_scheduled']]
            else:
                df = df[['candidate_name', 'match_score', 'is_shortlisted', 'interview_scheduled']]
            
            # Format table
            def color_score(val):
                color = 'green' if val >= 80 else 'orange' if val >= 50 else 'red'
                return f'color: {color}; font-weight: bold'
            
            st.dataframe(
                df.style.applymap(color_score, subset=['match_score']),
                height=min(400, len(matches) * 35 + 40),
                use_container_width=True
            )
            
            # Show details for selected match
            if selected_job_id:
                selected_match_id = st.selectbox(
                    "Select a match to view details",
                    options=[match['id'] for match in matches],
                    format_func=lambda x: f"{next(match['candidate_name'] for match in matches if match['id'] == x)} - {next(match['match_score'] for match in matches if match['id'] == x):.1f}%"
                )
                
                selected_match = next(match for match in matches if match['id'] == selected_match_id)
                candidate = db.get_candidate(selected_match['candidate_id'])
                job = db.get_job(selected_match['job_id'])
                
                if candidate and job:
                    st.markdown("### Match Details")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Job Requirements")
                        if job['summary']:
                            st.json(json.loads(job['summary']))
                        else:
                            st.warning("No summary available for this job")
                    
                    with col2:
                        st.markdown("#### Candidate Profile")
                        if candidate['extracted_data']:
                            st.json(json.loads(candidate['extracted_data']))
                        else:
                            st.warning("No extracted data available for this candidate")
                    
                    # Shortlist action
                    st.markdown("### Actions")
                    if not selected_match['is_shortlisted']:
                        if st.button("Shortlist Candidate"):
                            db.update_shortlist_status(selected_match['id'], True)
                            st.success("Candidate shortlisted!")
                            st.rerun()
                    else:
                        st.success("This candidate has been shortlisted!")
                        
                        if not selected_match['interview_scheduled']:
                            with st.form("schedule_interview_form"):
                                interview_date = st.date_input("Interview Date")
                                interview_time = st.time_input("Interview Time")
                                
                                if st.form_submit_button("Schedule Interview"):
                                    try:
                                        # Validate inputs
                                        if not interview_date or not interview_time:
                                            st.error("Please select both date and time")
                                            st.stop()
                                            
                                        interview_datetime = f"{interview_date} {interview_time}"
                                        
                                        # Update database
                                        db.schedule_interview(selected_match['id'], interview_datetime)
                                        
                                        # Generate and send email
                                        scheduler = InterviewScheduler()
                                        email_result = scheduler.generate_interview_email(
                                            job_title=job['title'],
                                            candidate_name=candidate['name'],
                                            candidate_email=candidate.get('email'),  # Safe get in case email is None
                                            match_details={
                                                'match_score': selected_match['match_score'],
                                                'job_id': selected_match['job_id'],
                                                'interview_time': interview_datetime
                                            },
                                            interview_date=interview_datetime
                                        )
                                        
                                        if email_result['success']:
                                            # Show success UI
                                            st.success("Interview scheduled and email sent successfully!")
                                            
                                            # Email preview expander
                                            with st.expander("View Email Content", expanded=True):
                                                st.write("**Subject:**", email_result['email_content']['subject'])
                                                st.text_area("Body", 
                                                            email_result['email_content'].get('html_body', email_result['email_content']['body']), 
                                                            height=200)
                                            
                                            # Add to activity log
                                            db.add_feedback(
                                                selected_match['id'],
                                                f"Interview scheduled for {interview_datetime}. Email sent: {email_result['email_content']['subject']}"
                                            )
                                        else:
                                            # Show partial success (scheduled but email failed)
                                            st.warning(f"Interview scheduled but email failed: {email_result.get('error', 'Unknown error')}")
                                            
                                            # Show troubleshooting info
                                            with st.expander("Error Details", expanded=False):
                                                st.write(email_result)
                                                if 'email_content' in email_result:
                                                    st.write("Generated Content:", email_result['email_content'])
                                        
                                        # Force UI update
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Failed to schedule interview: {str(e)}")
                                        logger.exception("Interview scheduling error")
                                        st.stop()
                        else:
                            st.info(f"Interview scheduled for {selected_match['interview_date']}")
        else:
            st.info("No matches found with the selected criteria")

elif selected_page == "Interview Scheduling":
    st.title("📅 Interview Scheduling")
    
    # Get shortlisted candidates
    shortlisted_matches = [m for m in db.get_matches() if m['is_shortlisted']]
    
    if not shortlisted_matches:
        st.info("No candidates have been shortlisted yet.")
    else:
        st.subheader("Shortlisted Candidates")
        
        # Group by job
        jobs = db.get_jobs()
        for job in jobs:
            job_matches = [m for m in shortlisted_matches if m['job_id'] == job['id']]
            if not job_matches:
                continue
                
            with st.expander(f"{job['title']} ({len(job_matches)} candidates)"):
                for match in job_matches:
                    candidate = db.get_candidate(match['candidate_id'])
                    
                    col1, col2, col3 = st.columns([2, 1, 2])
                    with col1:
                        st.markdown(f"**{candidate['name']}**")
                        st.write(f"Email: {candidate['email'] or 'Not available'}")
                        st.write(f"Match Score: {match['match_score']:.1f}%")
                    
                    with col2:
                        if match['interview_scheduled']:
                            st.success("✅ Scheduled")
                            st.write(match['interview_date'])
                        else:
                            st.warning("⏳ Pending")
                    
                    with col3:
                        if not match['interview_scheduled']:
                            if st.button(f"Schedule Interview", key=f"schedule_{match['id']}"):
                                st.session_state['schedule_match_id'] = match['id']
                                st.session_state['schedule_job_title'] = job['title']
                                st.session_state['schedule_candidate_name'] = candidate['name']
                                st.session_state['schedule_candidate_email'] = candidate['email']
                                st.rerun()
                        else:
                            if st.button(f"View Details", key=f"details_{match['id']}"):
                                st.session_state['view_match_id'] = match['id']
                                st.rerun()
        
        # Schedule interview for selected candidate
        if 'schedule_match_id' in st.session_state:
            match_id = st.session_state['schedule_match_id']
            match = next(m for m in shortlisted_matches if m['id'] == match_id)
            candidate_email = st.session_state['schedule_candidate_email']
            
            st.markdown("---")
            st.subheader(f"Schedule Interview: {st.session_state['schedule_candidate_name']} for {st.session_state['schedule_job_title']}")
            
            with st.form("schedule_interview_form"):
                interview_date = st.date_input("Interview Date")
                interview_time = st.time_input("Interview Time")
                interview_notes = st.text_area("Additional Notes for Candidate", 
                                             "Please bring any relevant documents or portfolio items.")
                
                if st.form_submit_button("Schedule & Send Invitation"):
                    interview_datetime = f"{interview_date} {interview_time}"
                    db.schedule_interview(match_id, interview_datetime)
                    
                    # Generate and send email
                    scheduler = InterviewScheduler()
                    email_result = scheduler.generate_interview_email(
                        job_title=st.session_state['schedule_job_title'],
                        candidate_name=st.session_state['schedule_candidate_name'],
                        candidate_email=candidate_email,
                        match_details={
                            'match_score': match['match_score'],
                            'job_title': st.session_state['schedule_job_title'],
                            'candidate_name': st.session_state['schedule_candidate_name']
                        },
                        interview_date=interview_datetime
                    )
                    
                    if email_result['success']:
                        st.success("Interview scheduled and invitation sent!")
                        st.markdown("### Email Preview")
                        st.write(f"**Subject:** {email_result['email_content']['subject']}")
                        st.write(f"**Body:**")
                        st.text(email_result['email_content']['body'])
                        
                        # Add email content to database
                        db.add_feedback(match_id, f"Interview scheduled for {interview_datetime}. Email sent to candidate.")
                    else:
                        st.error(f"Failed to send email: {email_result.get('error', 'Unknown error')}")
                        st.markdown("### Email Content (Not Sent)")
                        st.text(email_result.get('email_content', {}).get('body', 'No content generated'))
                    
                    # Clear session state
                    del st.session_state['schedule_match_id']
                    del st.session_state['schedule_job_title']
                    del st.session_state['schedule_candidate_name']
                    del st.session_state['schedule_candidate_email']
                    st.rerun()
        
        # View interview details
        if 'view_match_id' in st.session_state:
            match_id = st.session_state['view_match_id']
            match = next(m for m in shortlisted_matches if m['id'] == match_id)
            candidate = db.get_candidate(match['candidate_id'])
            job = db.get_job(match['job_id'])
            
            st.markdown("---")
            st.subheader(f"Interview Details: {candidate['name']} for {job['title']}")
            
            st.write(f"**Scheduled Time:** {match['interview_date']}")
            
            # For resending invitations:
            if st.button("Resend Interview Invitation"):
                if candidate['email']:
                    scheduler = InterviewScheduler()
                    email_result = scheduler.generate_interview_email(
                        job_title=job['title'],
                        candidate_name=candidate['name'],
                        candidate_email=candidate['email'],
                        match_details={
                            'match_score': match['match_score'],
                            'job_id': match['job_id'],
                            'candidate_id': match['candidate_id']
                        },
                        interview_date=match['interview_date']
                    )
                    
                    if email_result['success']:
                        st.success("Interview invitation resent!")
                        st.markdown("### Email Content")
                        st.json(email_result['email_content'])
                    else:
                        error_msg = email_result.get('error', 'Unknown error')
                        st.error(f"Failed to resend email: {error_msg}")
                        
                        # Show troubleshooting info
                        with st.expander("Troubleshooting Details"):
                            st.write("Error Details:", error_msg)
                            st.write("Prompt Used:", prompt)  # You'll need to make prompt available here
                else:
                    st.error("No email address available for this candidate")
            
            # Add feedback
            with st.form("add_feedback_form"):
                feedback = st.text_area("Interview Feedback", match.get('feedback', ''))
                
                if st.form_submit_button("Save Feedback"):
                    db.add_feedback(match_id, feedback)
                    st.success("Feedback saved!")
                    st.rerun()
            
            if st.button("Back to list"):
                del st.session_state['view_match_id']
                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #7f8c8d; font-size: 0.9em;">
        <p>RecruitFlow • Powered by Groq LLM and Streamlit</p>
    </div>
""", unsafe_allow_html=True)