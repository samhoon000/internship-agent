import sys
import os
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Append parent directory to system path for clean imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from internship_agent.config import DATABASE_PATH
from internship_agent.database.db import get_db_session, init_db, save_internships
from internship_agent.database.models import Internship
from internship_agent.scoring.legitimacy import get_legitimacy_bucket
from internship_agent.scrapers.internshala import InternshalaScraper
from internship_agent.scrapers.wellfound import WellfoundScraper
from internship_agent.scrapers.yc_jobs import YCJobsScraper
from internship_agent.scrapers.indeed import IndeedScraper

# Set page configurations
st.set_page_config(
    page_title="AI Internship Discovery Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium UI styling and typography
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6C63FF 0%, #3B82F6 50%, #10B981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.2rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(5px);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    .legit-badge {
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 8px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to query internships
def load_data_from_db():
    session = get_db_session()
    try:
        query = session.query(Internship).all()
        data = [item.to_dict() for item in query]
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return pd.DataFrame()
    finally:
        session.close()

# Initialize DB on start
init_db()

# Load Data
df = load_data_from_db()

# Sidebar Setup
st.sidebar.markdown("<h2 style='text-align: center;'>🎛️ Control Panel</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 1. Search Bar
search_query = st.sidebar.text_input("🔍 Search Internships", placeholder="Role, Company, Skills...")

# 2. Paid Only Filter
paid_only = st.sidebar.checkbox("💰 Paid Internships Only", value=True)

# 3. Remote Filter
remote_only = st.sidebar.checkbox("🏠 Remote Only", value=False)

# 4. Source Filter
if not df.empty:
    all_sources = list(df['source'].unique())
else:
    all_sources = ["Internshala", "Wellfound", "YC Jobs", "Indeed India"]
selected_sources = st.sidebar.multiselect("🌐 Data Sources", options=all_sources, default=all_sources)

# 5. Legitimacy Slider
min_legit_score = st.sidebar.slider("🛡️ Min Legitimacy Score", min_value=0, max_value=100, value=40)

# Apply Filter logic
if not df.empty:
    filtered_df = df.copy()
    
    # Text search
    if search_query:
        search_lower = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['role'].str.lower().str.contains(search_lower) |
            filtered_df['company_name'].str.lower().str.contains(search_lower) |
            filtered_df['skills'].str.lower().str.contains(search_lower)
        ]
        
    # Paid
    if paid_only:
        filtered_df = filtered_df[filtered_df['paid'] == True]
        
    # Remote
    if remote_only:
        filtered_df = filtered_df[filtered_df['remote'] == True]
        
    # Source
    filtered_df = filtered_df[filtered_df['source'].isin(selected_sources)]
    
    # Legitimacy
    filtered_df = filtered_df[filtered_df['legitimacy_score'] >= min_legit_score]
else:
    filtered_df = pd.DataFrame()

# Main Interface
st.markdown("<h1 class='main-title'>🤖 AI Internship Discovery Agent</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Real-time premium aggregator & legitimacy scoring engine for tech internships</p>", unsafe_allow_html=True)

# Main Dashboard statistics layout
col1, col2, col3, col4 = st.columns(4)

total_jobs = len(df) if not df.empty else 0
filtered_jobs = len(filtered_df) if not filtered_df.empty else 0

highly_legit = len(df[df['legitimacy_score'] >= 80]) if not df.empty else 0
avg_legit = df['legitimacy_score'].mean() if not df.empty else 0

with col1:
    st.markdown(f"""
    <div class='metric-card'>
        <h3>📁 Total Scraped</h3>
        <h2 style='color: #6C63FF;'>{total_jobs}</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='metric-card'>
        <h3>🎯 Filtered Match</h3>
        <h2 style='color: #3B82F6;'>{filtered_jobs}</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class='metric-card'>
        <h3>🛡️ Highly Legit (80+)</h3>
        <h2 style='color: #10B981;'>{highly_legit}</h2>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class='metric-card'>
        <h3>📈 Avg Legit Score</h3>
        <h2 style='color: #F59E0B;'>{avg_legit:.1f} / 100</h2>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Run Agent Button Action
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Manual Execution")
if st.sidebar.button("🚀 Run Discovery Scrapers Now", use_container_width=True):
    with st.spinner("Executing scrapers, applying filters, and checking legitimacy score..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        scrapers = [
            (InternshalaScraper(), 25, "Running Internshala module..."),
            (WellfoundScraper(), 50, "Running Wellfound module (Live & Fallback)..."),
            (YCJobsScraper(), 75, "Running YC Jobs module (Live & Fallback)..."),
            (IndeedScraper(), 100, "Running Indeed India module...")
        ]
        
        all_scraped = []
        for scraper, percentage, msg in scrapers:
            status_text.text(msg)
            try:
                scraped_data = scraper.scrape()
                all_scraped.extend(scraped_data)
            except Exception as e:
                st.sidebar.error(f"{scraper.source_name} failed: {e}")
            progress_bar.progress(percentage)
            
        status_text.text("Saving internships and filtering duplicates...")
        
        # Save to DB
        added, updated, skipped = save_internships(all_scraped)
        
        # Reload
        df = load_data_from_db()
        # Re-apply filters
        if not df.empty:
            filtered_df = df.copy()
            if search_query:
                search_lower = search_query.lower()
                filtered_df = filtered_df[
                    filtered_df['role'].str.lower().str.contains(search_lower) |
                    filtered_df['company_name'].str.lower().str.contains(search_lower) |
                    filtered_df['skills'].str.lower().str.contains(search_lower)
                ]
            if paid_only:
                filtered_df = filtered_df[filtered_df['paid'] == True]
            if remote_only:
                filtered_df = filtered_df[filtered_df['remote'] == True]
            filtered_df = filtered_df[filtered_df['source'].isin(selected_sources)]
            filtered_df = filtered_df[filtered_df['legitimacy_score'] >= min_legit_score]
        
        st.toast(f"Scrape completed! Added: {added}, Updated: {updated}", icon="✅")
        status_text.empty()
        progress_bar.empty()
        st.rerun()

# Split page into main table and visualizations
tab1, tab2 = st.tabs(["📋 Internship Postings", "📊 Analytics & Charts"])

with tab1:
    if filtered_df.empty:
        st.info("No internships match the selected filters. Use the sidebar to expand your search or trigger manual scraping.")
    else:
        # Create a beautiful display version of the dataframe
        display_df = filtered_df.copy()
        
        # Sort by legitimacy score descending
        display_df = display_df.sort_values(by="legitimacy_score", ascending=False)
        
        # Format Paid and Remote columns as nice emojis
        display_df['paid'] = display_df['paid'].map({True: "🟢 Yes", False: "🔴 No"})
        display_df['remote'] = display_df['remote'].map({True: "🏠 Remote", False: "🏢 On-site"})
        
        # Assign legitimacy bucket
        display_df['legitimacy_bucket'] = display_df['legitimacy_score'].apply(get_legitimacy_bucket)
        
        # Reorder and pick columns for neat view
        cols_to_show = [
            "company_name", "role", "stipend", "paid", "location", "remote", 
            "duration", "skills", "legitimacy_score", "legitimacy_bucket", "source", "apply_link"
        ]
        display_df = display_df[cols_to_show]
        
        # Clean column headers
        display_df.columns = [col.replace("_", " ").title() for col in display_df.columns]
        
        # Streamlit interactive dataframe rendering
        st.dataframe(
            display_df,
            column_config={
                "Apply Link": st.column_config.LinkColumn("Apply Link", display_text="Open Listing 🔗"),
                "Legitimacy Score": st.column_config.ProgressColumn(
                    "Legitimacy Score",
                    help="Trustworthiness score from 0 to 100",
                    format="%d",
                    min_value=0,
                    max_value=100
                ),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # CSV Export Button
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Current Filtered Results to CSV",
            data=csv_data,
            file_name=f"legit_internships_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

with tab2:
    if df.empty:
        st.info("Visualizations will appear here once internships are loaded into the database.")
    else:
        # Analytics visualizer
        st.markdown("### 📊 Metrics Deep Dive")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Chart 1: Internships by source
            source_counts = df['source'].value_counts().reset_index()
            source_counts.columns = ['Source', 'Total Postings']
            fig_source = px.pie(
                source_counts, 
                values='Total Postings', 
                names='Source', 
                title='Internships Volume by Source Platform',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_source.update_layout(template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
            st.plotly_chart(fig_source, use_container_width=True)
            
        with col_chart2:
            # Chart 2: Legitimacy scores distribution
            df['Legitimacy Category'] = df['legitimacy_score'].apply(get_legitimacy_bucket)
            legit_counts = df['Legitimacy Category'].value_counts().reset_index()
            legit_counts.columns = ['Category', 'Volume']
            fig_legit = px.bar(
                legit_counts,
                x='Category',
                y='Volume',
                title='Legitimacy Scores Breakdown',
                color='Category',
                color_discrete_map={
                    "Highly Legit": "#10B981",
                    "Good": "#3B82F6",
                    "Risky": "#F59E0B",
                    "Avoid": "#EF4444"
                }
            )
            fig_legit.update_layout(template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
            st.plotly_chart(fig_legit, use_container_width=True)
            
        col_chart3, col_chart4 = st.columns(2)
        
        with col_chart3:
            # Chart 3: Top locations
            loc_counts = df['location'].value_counts().head(8).reset_index()
            loc_counts.columns = ['Location', 'Volume']
            fig_loc = px.bar(
                loc_counts,
                x='Volume',
                y='Location',
                orientation='h',
                title='Top 8 Internship Cities / Locations',
                color_discrete_sequence=['#6C63FF']
            )
            fig_loc.update_layout(template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
            st.plotly_chart(fig_loc, use_container_width=True)
            
        with col_chart4:
            # Chart 4: Remote vs On-site distribution
            remote_counts = df['remote'].map({True: 'Remote (WFH)', False: 'On-site'}).value_counts().reset_index()
            remote_counts.columns = ['Work Type', 'Volume']
            fig_remote = px.pie(
                remote_counts,
                values='Volume',
                names='Work Type',
                title='Remote Work Flexibility Split',
                color_discrete_sequence=['#10B981', '#6C63FF']
            )
            fig_remote.update_layout(template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white")
            st.plotly_chart(fig_remote, use_container_width=True)
