import streamlit as st
from intelligence_hub.ui.components import (
    render_company_profile,
    render_financials_detailed,
    render_chart,
    render_competitors,
    render_insights_strategic,
    render_sources,
    render_pdf_analysis,
    render_references
)

def render_main_dashboard(placeholder=None):
    """
    Renders the main intelligence dashboard using modular components.
    Designed for asynchronous updates and professional layout.
    """
    if placeholder is None:
        placeholder = st.empty()
    
    
    # Inject Dashboard-specific CSS - Enhanced to match UI theme
    st.markdown("""
    <style>
        /* Dashboard Container */
        .dashboard-container {
            margin-top: 40px;
            padding: 0;
        }
        
        /* Dashboard Section Card - Premium Styling */
        .dash-section-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.95) 100%);
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 4px 20px rgba(0, 51, 102, 0.08);
            border: 1px solid rgba(0, 51, 102, 0.1);
            margin-bottom: 28px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(10px);
        }
        
        .dash-section-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(0, 80, 158, 0.12);
            border-color: rgba(0, 119, 255, 0.2);
        }
        
        /* Dashboard Section Header */
        .dash-section-header {
            color: #003366;
            font-family: 'Poppins', sans-serif;
            font-weight: 700;
            font-size: 1.3rem;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding-bottom: 12px;
            border-bottom: 2px solid rgba(0, 51, 102, 0.1);
            letter-spacing: -0.01em;
        }
        
        .dash-section-header::before {
            content: '';
            width: 4px;
            height: 24px;
            background: linear-gradient(180deg, #003366 0%, #0077ff 100%);
            border-radius: 2px;
        }
        
        /* Dashboard Highlight Card */
        .dash-highlight-card {
            background: linear-gradient(135deg, #003366 0%, #00509e 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0, 51, 102, 0.25);
        }
        
        .dash-highlight-card h3 {
            color: white !important;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 12px;
        }
        
        /* Dashboard Metric Card */
        .dash-metric {
            background: rgba(255, 255, 255, 0.6);
            border-radius: 10px;
            padding: 16px;
            margin: 8px 0;
            border-left: 3px solid #0077ff;
            transition: all 0.2s ease;
        }
        
        .dash-metric:hover {
            background: rgba(255, 255, 255, 0.9);
            transform: translateX(4px);
        }
        
        .dash-metric-label {
            font-size: 0.85rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .dash-metric-value {
            font-size: 1.4rem;
            color: #003366;
            font-weight: 700;
            font-family: 'Poppins', sans-serif;
        }
        
        /* Dashboard Grid Layout */
        .dash-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        /* Dashboard List Items */
        .dash-list-item {
            padding: 12px 16px;
            background: rgba(248, 250, 252, 0.5);
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 3px solid #00509e;
            transition: all 0.2s ease;
        }
        
        .dash-list-item:hover {
            background: rgba(248, 250, 252, 0.9);
            transform: translateX(4px);
            border-left-color: #0077ff;
        }
        
        /* Dashboard Badge */
        .dash-badge {
            display: inline-block;
            padding: 4px 12px;
            background: linear-gradient(135deg, #0077ff 0%, #00509e 100%);
            color: white;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 4px;
            box-shadow: 0 2px 6px rgba(0, 119, 255, 0.3);
        }
        
        /* Dashboard Info Box */
        .dash-info-box {
            background: rgba(0, 119, 255, 0.05);
            border: 1px solid rgba(0, 119, 255, 0.2);
            border-radius: 10px;
            padding: 16px;
            margin: 16px 0;
        }
        
        .dash-info-box p {
            margin: 0;
            color: #003366;
            line-height: 1.6;
        }
    </style>
    """, unsafe_allow_html=True)

    with placeholder.container():
        # Only show dashboard after analysis is complete (after user clicks continue button)
        # Do not show during enrichment phase or when investigation is paused
        if not st.session_state.get("analysis_complete", False):
            return

        # Check if we have any data to show
        if not st.session_state.get("data"):
            # If no data, render nothing
            return

        data = st.session_state.get("data", {})
        
        # Dashboard Header - Professional Section Label
        st.markdown("""
        <div style="margin-top: 48px; margin-bottom: 32px;">
            <div class="ui-section-label" style="font-size: 18px; margin-bottom: 8px;">
                <span class="emoji" style="font-size: 24px;">📊</span>
                <span style="font-weight: 700; color: #003366;">Final Intelligence Dashboard</span>
            </div>
            <div style="font-size: 14px; color: #64748b; margin-left: 36px; font-style: italic;">
                Comprehensive analysis and insights for the investigated entity
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 1. Company Profile (Always First)
        # Check for meta to ensure we have basic info
        if "meta" in data:
            st.markdown('<div class="dash-section-card">', unsafe_allow_html=True)
            render_company_profile(data) 
            st.markdown('</div>', unsafe_allow_html=True)

        # 2. Financials & Market Data
        if "financials" in data:
            st.markdown('<div class="dash-section-card">', unsafe_allow_html=True)
            render_financials_detailed(data)
            st.markdown('</div>', unsafe_allow_html=True)
            
        if "chart" in data and data["chart"]:
                 st.markdown('<div class="dash-section-card">', unsafe_allow_html=True)
                 render_chart(data)
                 st.markdown('</div>', unsafe_allow_html=True)

        # 3. Competitors
        if "competitors" in data and data["competitors"]:
            st.markdown('<div class="dash-section-card">', unsafe_allow_html=True)
            render_competitors(data)
            st.markdown('</div>', unsafe_allow_html=True)

        # 4. Strategic Insights 
        if "insights" in data and data["insights"]:
            st.markdown('<div class="dash-section-card" style="border-left: 5px solid #003366;">', unsafe_allow_html=True)
            render_insights_strategic(data)
            st.markdown('</div>', unsafe_allow_html=True)

        # 5. Document Analysis (PDF)
        if "pdf_results" in data and data["pdf_results"]:
            st.markdown('<div class="dash-section-card">', unsafe_allow_html=True)
            render_pdf_analysis(data)
            st.markdown('</div>', unsafe_allow_html=True)
            
        # 6. References & Sources
        st.markdown('<div class="dash-section-card">', unsafe_allow_html=True)
        render_references(data)
        st.markdown('</div>', unsafe_allow_html=True)
