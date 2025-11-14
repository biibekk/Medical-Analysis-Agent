import streamlit as st
import json
import os
from datetime import datetime, time, timedelta
from pathlib import Path
import sqlite3
import pandas as pd
from typing import List, Dict, Optional
import plotly.graph_objects as go
import plotly.express as px
import hashlib
import re
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import your existing analyzer
from medical_analyzer import (
    app as analyzer_workflow,
    generate_user_friendly_output,
    generate_pdf_report,
    llm
)

# Page configuration
st.set_page_config(
    page_title="Medical Analysis Agent - Your Personal Medical Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# for sidebar
# linear-gradient(135deg, #6a9ff8, #b0d4ff) !important;
# linear-gradient(135deg, #43cea2, #185a9d) !important;
# linear-gradient(135deg, #a1c4fd, #c2e9fb) !important; this one
# linear-gradient(135deg, #83a4d4, #b6fbff) !important;
# linear-gradient(135deg, #e0eafc, #cfdef3) !important;


# Professional Custom CSS with Modern Design
st.markdown("""
<style>
    /* Sidebar background - Professional Medical Theme */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #a1c4fd, #c2e9fb) !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(135deg, #a1c4fd, #c2e9fb) !important;
    }
    
    [data-testid="stSidebarContent"] {
        background: linear-gradient(135deg, #a1c4fd, #c2e9fb) !important;
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(135deg, #a1c4fd, #c2e9fb) !important;
    }
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* header {visibility: hidden;} */
    
    /* Main Container */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 0;
    }
    
    /* Hero Header */
    .hero-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        animation: fadeIn 0.8s ease-in;
    }
    
    .hero-header h1 {
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(to right, #fff, #e0e7ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .hero-header p {
        font-size: 1.2rem;
        margin-top: 1rem;
        opacity: 0.95;
    }
    
    /* Card Components */
    .modern-card {
        background: whitesmoke;
        border-radius: 16px;
        padding: 0.8rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin: 0 0 1rem 0;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    
    /* Stat Cards */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stat-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: pulse 3s ease-in-out infinite;
    }
    
    .stat-card:hover {
        transform: scale(1.05);
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
    }
    
    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Alert Boxes */
    .alert-box {
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border-left: 4px solid;
        animation: slideIn 0.5s ease;
    }
    
    .alert-success {
        background: #d4edda;
        border-color: #28a745;
        color: #155724;
    }
    
    .alert-warning {
        background: #fff3cd;
        border-color: #ffc107;
        color: #856404;
    }
    
    .alert-danger {
        background: #f8d7da;
        border-color: #dc3545;
        color: #721c24;
    }
    
    .alert-info {
        background: #d1ecf1;
        border-color: #17a2b8;
        color: #0c5460;
    }
    
    /* Auth Container */
    .auth-container {
        max-width: 480px;
        margin: 4rem auto;
        background: white;
        border-radius: 24px;
        padding: 3rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        animation: fadeInUp 0.6s ease;
    }
    
    .auth-header {
        text-align: center;
        margin-bottom: 2.5rem;
    }
    
    .auth-header h2 {
        color: #667eea;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .auth-header p {
        color: #666;
        font-size: 1rem;
    }
    
    /* Form Inputs */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {
        border-radius: 10px !important;
        border: 2px solid #e0e7ff !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput input:focus, .stSelectbox select:focus, .stTextArea textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 10px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        border: none !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
    }
    
    .stButton button[kind="secondary"] {
        background: white !important;
        color: #667eea !important;
        border: 2px solid #667eea !important;
    }
    
    .stButton button[kind="secondary"]:hover {
        background: #f0f4ff !important;
    }
    
    /* Chat Messages */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
    }
    
    .chat-message {
        padding: 1.5rem;
        border-radius: 16px;
        margin: 1rem 0;
        animation: messageSlide 0.4s ease;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        /* linear-gradient(135deg, #a1c4fd, #c2e9fb) */
        color: white;
        /* #3948f6 */
        margin-left: 15%;
        border-bottom-right-radius: 4px;
    }
    
    .assistant-message {
        /*
        background: white;
        color: #333;
        margin-right: 15%;
        border: 1px solid #e0e7ff;
        border-bottom-left-radius: 4px;
        */        
   
        margin-right: 15%;
        border-left: 4px solid rgba(142, 187, 142, 0.82); 
        border-bottom-left-radius: 4px;
        background: rgba(152, 251, 152, 0.26);
        padding: 1.5rem;
        line-height: 1.8;
        font-size: 1rem;
        color: #333;
    }
    
    /* Progress Indicators */
    .progress-container {
        margin: 2rem 0;
    }
    
    .progress-step {
        display: flex;
        align-items: center;
        margin: 1rem 0;
        padding: 1rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .progress-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        margin-right: 1rem;
    }
    
    /* Report Cards */
    .report-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }
    
    .report-card:hover {
        transform: translateX(5px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.12);
    }
    
    /* Test Result Status */
    .test-status {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-normal {
        background: #d4edda;
        color: #155724;
    }
    
    .status-high {
        background: #f8d7da;
        color: #721c24;
    }
    
    .status-low {
        background: #fff3cd;
        color: #856404;
    }
    
    /* Loading Animation */
    .loading-container {
        text-align: center;
        padding: 3rem;
    }
    
    .loader {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        animation: spin 1s linear infinite;
        margin: 0 auto;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes messageSlide {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 1; }
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .hero-header h1 {
            font-size: 2rem;
        }
        
        .auth-container {
            margin: 2rem 1rem;
            padding: 2rem;
        }
        
        .user-message, .assistant-message {
            margin-left: 0 !important;
            margin-right: 0 !important;
        }
    }
    
    /* Feature Cards */
    .feature-card {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        border: 2px solid transparent;
    }
    
    .feature-card:hover {
        border-color: #667eea;
        transform: translateY(-10px);
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.2);
    }
    
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    .feature-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 0.5rem;
    }
    
    .feature-description {
        color: #666;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    /* Metric Cards */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border-left: 4px solid;
    }
    
    .metric-card.success { border-color: #28a745; }
    .metric-card.warning { border-color: #ffc107; }
    .metric-card.danger { border-color: #dc3545; }
    .metric-card.info { border-color: #17a2b8; }
    
    /* Timeline */
    .timeline-item {
        position: relative;
        padding-left: 3rem;
        padding-bottom: 2rem;
        border-left: 2px solid #e0e7ff;
    }
    
    .timeline-item::before {
        content: '';
        position: absolute;
        left: -7px;
        top: 0;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #667eea;
        border: 3px solid white;
        box-shadow: 0 0 0 2px #667eea;
    }
    
    /* Tabs Enhancement */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* File Uploader */
    .uploadedFile {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        border: 2px dashed #667eea;
    }
    
    /* Success Animation */
    .success-checkmark {
        width: 80px;
        height: 80px;
        margin: 0 auto;
    }
    
    .check-icon {
        width: 80px;
        height: 80px;
        position: relative;
        border-radius: 50%;
        box-sizing: content-box;
        border: 4px solid #4CAF50;
    }
    
    .check-icon::before {
        top: 3px;
        left: -2px;
        width: 30px;
        transform-origin: 100% 50%;
        border-radius: 100px 0 0 100px;
    }
    
    .check-icon::after {
        top: 0;
        left: 30px;
        width: 60px;
        transform-origin: 0 50%;
        border-radius: 0 100px 100px 0;
        animation: rotate-circle 4.25s ease-in;
    }
</style>
""", unsafe_allow_html=True)

# style for summary and recommendations
st.markdown("""
<style>
    .summary-box-style{
        border-left: 4px solid lightblue;
        background: aliceblue; 
        padding: 1.5rem; 
        border-radius: 12px; 
        line-height: 1.8; 
        font-size: 1rem; 
        color: #333;
    }
    
    .recommendation-box-style{
        background: linear-gradient(135deg, rgb(255, 243, 205) 0%, rgb(255, 229, 160) 100%);
        padding: 0 1.5rem .5rem 1.5rem;
        border-radius: 12px;
        line-height: 1.8;
        font-size: 1rem;
        color: rgb(133, 100, 4);  
        border-left: 4px solid rgb(246, 213, 116);     
    }
    
            
</style>
""",unsafe_allow_html=True)


# custom style for grid view in history section
st.markdown("""
    <style>
        .report-card {
            background: whitesmoke;
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .report-header {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }
        .report-icon {
            font-size: 1.5rem;
            margin-right: 0.75rem;
        }
        .report-title {
            margin: 0;
            color: #333;
            font-size: 1.1rem;
            font-weight: 600;
        }
        .report-date {
            color: #666;
            font-size: 0.9rem;
            margin: 0 0 1.5rem 0;
        }
        .report-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }
        .stat-item2 {
            text-align: center;
        }
        .stat-label2 {
            font-size: 0.8rem;
            color: #666;
            margin-bottom: 0.25rem;
        }
        .stat-value2 {
            font-size: 1.8rem;
            font-weight: 700;
            color: #333;
        }
    </style>
""", unsafe_allow_html=True)


# Email Configuration
class EmailService:
    """Production-ready email service for OTP and notifications."""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'Medical Analysis Agent')
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """Send email with HTML and plain text fallback."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            st.error(f"Email error: {str(e)}")
            return False
    
    def send_otp(self, to_email: str, otp: str, purpose: str = "verification") -> bool:
        """Send OTP verification email with professional template."""
        subject = f"Your Medical Analysis Agent Verification Code"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Helvetica Neue', Arial, sans-serif; 
                    line-height: 1.6; 
                    color: #333; 
                    margin: 0;
                    padding: 0;
                    background: #f5f7fa;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 40px auto; 
                    background: white;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    padding: 40px 30px; 
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 700;
                }}
                .content {{ 
                    padding: 40px 30px;
                }}
                .otp-box {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 12px;
                    padding: 30px; 
                    text-align: center; 
                    font-size: 42px; 
                    font-weight: 700; 
                    letter-spacing: 12px; 
                    color: white;
                    margin: 30px 0;
                    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
                }}
                .info-box {{
                    background: #f8f9fa;
                    border-left: 4px solid #667eea;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .footer {{ 
                    text-align: center; 
                    padding: 30px;
                    background: #f8f9fa;
                    color: #666; 
                    font-size: 13px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white !important;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 Medical Analysis Agent</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Your Personal Medical Assistant</p>
                </div>
                <div class="content">
                    <h2 style="color: #333; margin-top: 0;">Account Verification</h2>
                    <p style="font-size: 16px; color: #555;">Hi there! 👋</p>
                    <p style="font-size: 16px; color: #555;">
                        Thank you for choosing Medical Analysis Agent. To complete your {purpose}, 
                        please use the verification code below:
                    </p>
                    <div class="otp-box">{otp}</div>
                    <div class="info-box">
                        <strong style="color: #667eea;">⏰ Valid for 10 minutes</strong><br>
                        <p style="margin: 10px 0 0 0; color: #666;">
                            Enter this code in the application to proceed with your {purpose}.
                        </p>
                    </div>
                    <div class="warning">
                        <strong>🔒 Security Tips:</strong><br>
                        <ul style="margin: 10px 0 0 0; padding-left: 20px; color: #666;">
                            <li>Never share this code with anyone</li>
                            <li>Medical Analysis Agent will never ask for this code via phone or email</li>
                            <li>If you didn't request this, please ignore this email</li>
                        </ul>
                    </div>
                    <p style="color: #666; margin-top: 30px;">
                        Need help? Contact our support team at 
                        <a href="mailto:support@mediscan.ai" style="color: #667eea;">support@mediscan.ai</a>
                    </p>
                </div>
                <div class="footer">
                    <p style="margin: 0;"><strong>Medical Analysis Agent</strong></p>
                    <p style="margin: 10px 0;">Your trusted medical report analysis platform</p>
                    <p style="margin: 10px 0; font-size: 12px;">
                        © 2024 Medical Analysis Agent. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Medical Analysis Agent - Account Verification
        
        Your verification code is: {otp}
        
        This code expires in 10 minutes.
        Never share this code with anyone.
        
        If you didn't request this code, please ignore this email.
        
        Need help? Contact: support@mediscan.ai
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_welcome_email(self, to_email: str, full_name: str) -> bool:
        """Send professional welcome email."""
        subject = "Welcome to Medical Analysis Agent! 🎉"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Helvetica Neue', Arial, sans-serif; 
                    line-height: 1.6; 
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background: #f5f7fa;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 40px auto; 
                    background: white;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    padding: 50px 30px; 
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 32px;
                    font-weight: 700;
                }}
                .content {{ 
                    padding: 40px 30px;
                }}
                .feature {{ 
                    background: #f8f9fa;
                    padding: 20px;
                    margin: 15px 0;
                    border-radius: 12px;
                    border-left: 4px solid #667eea;
                    transition: all 0.3s ease;
                }}
                .feature-icon {{
                    font-size: 24px;
                    margin-right: 10px;
                }}
                .cta-button {{
                    display: inline-block;
                    padding: 15px 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white !important;
                    text-decoration: none;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 20px 0;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                }}
                .footer {{ 
                    text-align: center; 
                    padding: 30px;
                    background: #f8f9fa;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to Medical Analysis Agent!</h1>
                    <p style="margin: 15px 0 0 0; font-size: 18px; opacity: 0.95;">
                        Your Journey to Better Health Understanding Begins Now
                    </p>
                </div>
                <div class="content">
                    <h2 style="color: #333;">Hello {full_name}! 👋</h2>
                    <p style="font-size: 16px; color: #555; line-height: 1.8;">
                        Thank you for joining <strong>Medical Analysis Agent</strong>. We're thrilled to have you on board! 
                        Our mission is to help you understand your medical reports with clarity and confidence.
                    </p>
                    
                    <h3 style="color: #667eea; margin-top: 35px;">✨ What You Can Do:</h3>
                    
                    <div class="feature">
                        <span class="feature-icon">📤</span>
                        <strong>Upload Medical Reports</strong><br>
                        <span style="color: #666; font-size: 14px;">
                            Simply upload your lab reports in PDF format for instant analysis
                        </span>
                    </div>
                    
                    <div class="feature">
                        <span class="feature-icon">🤖</span>
                        <strong>AI-Powered Analysis</strong><br>
                        <span style="color: #666; font-size: 14px;">
                            Get comprehensive insights and easy-to-understand explanations
                        </span>
                    </div>
                    
                    <div class="feature">
                        <span class="feature-icon">📈</span>
                        <strong>Track Health Trends</strong><br>
                        <span style="color: #666; font-size: 14px;">
                            Monitor your health metrics over time with beautiful visualizations
                        </span>
                    </div>
                    
                    <div class="feature">
                        <span class="feature-icon">💬</span>
                        <strong>Ask Questions</strong><br>
                        <span style="color: #666; font-size: 14px;">
                            Chat with our AI assistant about your health data anytime
                        </span>
                    </div>
                    
                    <div style="background: #fff3cd; padding: 20px; border-radius: 12px; margin: 30px 0; border-left: 4px solid #ffc107;">
                        <strong style="color: #856404;">⚠️ Important Reminder:</strong><br>
                        <p style="margin: 10px 0 0 0; color: #856404; font-size: 14px;">
                            Medical Analysis Agent is an informational tool. Always consult with your healthcare 
                            provider for medical advice, diagnosis, or treatment decisions.
                        </p>
                    </div>
                    
                    <div style="text-align: center; margin: 40px 0;">
                        <a href="#" class="cta-button">🚀 Start Your First Analysis</a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 30px;">
                        Questions or need assistance? We're here to help!<br>
                        📧 Email: <a href="mailto:support@mediscan.ai" style="color: #667eea;">support@mediscan.ai</a><br>
                        💬 Live Chat: Available 24/7 in the app
                    </p>
                </div>
                <div class="footer">
                    <p style="margin: 0; font-weight: 600;">Medical Analysis Agent</p>
                    <p style="margin: 10px 0; font-size: 13px;">
                        Empowering you with AI-driven health insights
                    </p>
                    <p style="margin: 10px 0; font-size: 12px;">
                        © 2024 Medical Analysis Agent. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)


# Enhanced Database (keep your existing MedicalDatabase class)
class MedicalDatabase:
    def __init__(self, db_path="medical_history.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables with security features."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            date_of_birth DATE,
            gender TEXT,
            phone_number TEXT,
            is_verified INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            account_locked_until TIMESTAMP
        )
        """)
        
        # OTP table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            purpose TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            ip_address TEXT
        )
        """)
        
        # Security log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            email TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Reports table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            filename TEXT,
            patient_age INTEGER,
            patient_gender TEXT,
            total_tests INTEGER,
            normal_count INTEGER,
            abnormal_count INTEGER,
            no_reference_count INTEGER,
            summary TEXT,
            recommendations TEXT,
            full_analysis TEXT,
            pdf_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        """)
        
        # Test results table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            test_name TEXT,
            test_value TEXT,
            units TEXT,
            status TEXT,
            reference_range TEXT,
            analysis TEXT,
            confidence TEXT,
            FOREIGN KEY (report_id) REFERENCES reports (id)
        )
        """)
        
        # Chat history
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            report_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            message TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (report_id) REFERENCES reports (id)
        )
        """)
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = os.getenv('PASSWORD_SALT', 'mediscan_ai_salt_2024')
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def generate_otp(self) -> str:
        """Generate 6-digit OTP."""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    def create_otp(self, email: str, purpose: str = "verification", ip_address: str = None) -> str:
        """Create and store OTP code."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        otp_code = self.generate_otp()
        expires_at = datetime.now() + timedelta(minutes=10)
        
        cursor.execute("""
        INSERT INTO otp_codes (email, otp_code, purpose, expires_at, ip_address)
        VALUES (?, ?, ?, ?, ?)
        """, (email.lower(), otp_code, purpose, expires_at, ip_address))
        
        conn.commit()
        conn.close()
        
        return otp_code
    
    def verify_otp(self, email: str, otp_code: str, purpose: str = "verification") -> bool:
        """Verify OTP code."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, expires_at FROM otp_codes
        WHERE email = ? AND otp_code = ? AND purpose = ? AND used = 0
        ORDER BY created_at DESC LIMIT 1
        """, (email.lower(), otp_code, purpose))
        
        result = cursor.fetchone()
        
        if result:
            otp_id, expires_at = result
            expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S.%f')
            
            if datetime.now() < expires_at:
                cursor.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (otp_id,))
                conn.commit()
                conn.close()
                return True
        
        conn.close()
        return False
    
    def create_user(self, email: str, password: str, full_name: str, 
                   date_of_birth: str = None, gender: str = None, phone_number: str = None) -> tuple[bool, str]:
        """Create new user account (unverified)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            user_id = f"user_{hashlib.md5(email.encode()).hexdigest()[:8]}"
            password_hash = self.hash_password(password)
            
            cursor.execute("""
            INSERT INTO users (user_id, email, password_hash, full_name, date_of_birth, gender, phone_number, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (user_id, email.lower(), password_hash, full_name, date_of_birth, gender, phone_number))
            
            conn.commit()
            
            # Log the action
            self.log_security_event(user_id, email, "account_created", "success")
            
            conn.close()
            return True, user_id
        
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Email already registered"
        except Exception as e:
            conn.close()
            return False, str(e)
    
    def verify_user_account(self, email: str) -> bool:
        """Mark user account as verified."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email.lower(),))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            self.log_security_event(None, email, "account_verified", "success")
        
        return affected > 0
    
    def authenticate_user(self, email: str, password: str, ip_address: str = None) -> Optional[Dict]:
        """Authenticate user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT user_id, account_locked_until, failed_login_attempts, is_verified, is_active
        FROM users WHERE email = ?
        """, (email.lower(),))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            self.log_security_event(None, email, "login_attempt", "failed_user_not_found", ip_address)
            return None
        
        user_id, locked_until, failed_attempts, is_verified, is_active = result
        
        if locked_until:
            locked_until_dt = datetime.strptime(locked_until, '%Y-%m-%d %H:%M:%S.%f')
            if datetime.now() < locked_until_dt:
                conn.close()
                self.log_security_event(user_id, email, "login_attempt", "failed_account_locked", ip_address)
                return None
            else:
                cursor.execute("""
                UPDATE users SET account_locked_until = NULL, failed_login_attempts = 0
                WHERE user_id = ?
                """, (user_id,))
                conn.commit()
        
        if not is_active:
            conn.close()
            self.log_security_event(user_id, email, "login_attempt", "failed_account_inactive", ip_address)
            return None
        
        password_hash = self.hash_password(password)
        
        cursor.execute("""
        SELECT user_id, email, full_name, date_of_birth, gender, phone_number, is_verified
        FROM users WHERE email = ? AND password_hash = ?
        """, (email.lower(), password_hash))
        
        user_result = cursor.fetchone()
        
        if user_result:
            cursor.execute("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP, failed_login_attempts = 0
            WHERE email = ?
            """, (email.lower(),))
            conn.commit()
            
            user_info = {
                'user_id': user_result[0],
                'email': user_result[1],
                'full_name': user_result[2],
                'date_of_birth': user_result[3],
                'gender': user_result[4],
                'phone_number': user_result[5],
                'is_verified': user_result[6]
            }
            
            self.log_security_event(user_id, email, "login", "success", ip_address)
            conn.close()
            return user_info
        else:
            failed_attempts += 1
            
            if failed_attempts >= 5:
                locked_until = datetime.now() + timedelta(minutes=30)
                cursor.execute("""
                UPDATE users SET failed_login_attempts = ?, account_locked_until = ?
                WHERE user_id = ?
                """, (failed_attempts, locked_until, user_id))
                self.log_security_event(user_id, email, "login_attempt", "failed_account_locked", ip_address)
            else:
                cursor.execute("""
                UPDATE users SET failed_login_attempts = ?
                WHERE user_id = ?
                """, (failed_attempts, user_id))
                self.log_security_event(user_id, email, "login_attempt", f"failed_wrong_password_attempt_{failed_attempts}", ip_address)
            
            conn.commit()
            conn.close()
            return None
    
    def reset_password(self, email: str, new_password: str) -> bool:
        """Reset user password."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = self.hash_password(new_password)
        
        cursor.execute("""
        UPDATE users SET password_hash = ?, failed_login_attempts = 0, account_locked_until = NULL
        WHERE email = ?
        """, (password_hash, email.lower(),))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            self.log_security_event(None, email, "password_reset", "success")
        
        return affected > 0
    
    def log_security_event(self, user_id: str, email: str, action: str, status: str, ip_address: str = None, user_agent: str = None):
        """Log security events."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO security_log (user_id, email, action, status, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, email, action, status, ip_address, user_agent))
        
        conn.commit()
        conn.close()
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT user_id, email, full_name, date_of_birth, gender, phone_number, 
               is_verified, created_at, last_login
        FROM users WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'user_id': result[0],
                'email': result[1],
                'full_name': result[2],
                'date_of_birth': result[3],
                'gender': result[4],
                'phone_number': result[5],
                'is_verified': result[6],
                'created_at': result[7],
                'last_login': result[8]
            }
        return None
    
    def save_report(self, user_id: str, output: dict, filename: str, pdf_path: str) -> int:
        """Save report to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        patient_info = output.get("patient_info", {})
        stats = output.get("statistics", {})
        
        cursor.execute("""
        INSERT INTO reports (
            user_id, filename, patient_age, patient_gender,
            total_tests, normal_count, abnormal_count, no_reference_count,
            summary, recommendations, full_analysis, pdf_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, filename, patient_info.get("age"), patient_info.get("gender"),
            stats.get("total_tests", 0), stats.get("normal_count", 0),
            stats.get("abnormal_count", 0), stats.get("no_reference_count", 0),
            output.get("summary", ""), output.get("recommendations", ""),
            json.dumps(output), pdf_path
        ))
        
        report_id = cursor.lastrowid
        
        for result in output.get("detailed_results", []):
            cursor.execute("""
            INSERT INTO test_results (
                report_id, test_name, test_value, units, status,
                reference_range, analysis, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id, result.get("test_name"), result.get("test_value"),
                result.get("units"), result.get("status"), result.get("reference_range"),
                result.get("analysis"), result.get("confidence")
            ))
        
        conn.commit()
        conn.close()
        
        return report_id
    
    def get_user_reports(self, user_id: str) -> List[Dict]:
        """Get all reports for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, report_date, filename, patient_age, patient_gender,
               total_tests, normal_count, abnormal_count, no_reference_count
        FROM reports WHERE user_id = ?
        ORDER BY report_date DESC
        """, (user_id,))
        
        columns = [desc[0] for desc in cursor.description]
        reports = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return reports
    
    def get_report_details(self, report_id: int) -> Dict:
        """Get detailed report information."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        columns = [desc[0] for desc in cursor.description]
        report = dict(zip(columns, cursor.fetchone()))
        
        cursor.execute("""
        SELECT test_name, test_value, units, status, reference_range, analysis
        FROM test_results WHERE report_id = ?
        """, (report_id,))
        
        test_columns = [desc[0] for desc in cursor.description]
        tests = [dict(zip(test_columns, row)) for row in cursor.fetchall()]
        
        report['test_results'] = tests
        conn.close()
        return report
    
    def get_test_trends(self, user_id: str, test_name: str) -> List[Dict]:
        """Get historical trends for a specific test."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT r.report_date, t.test_value, t.units, t.status
        FROM test_results t
        JOIN reports r ON t.report_id = r.id
        WHERE r.user_id = ? AND t.test_name = ?
        ORDER BY r.report_date
        """, (user_id, test_name))
        
        columns = [desc[0] for desc in cursor.description]
        trends = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return trends
    
    def save_chat_message(self, user_id: str, report_id: int, role: str, message: str):
        """Save chat message."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO chat_history (user_id, report_id, role, message)
        VALUES (?, ?, ?, ?)
        """, (user_id, report_id, role, message))
        
        conn.commit()
        conn.close()
    
    def get_chat_history(self, user_id: str, report_id: int = None) -> List[Dict]:
        """Get chat history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if report_id:
            cursor.execute("""
            SELECT timestamp, role, message
            FROM chat_history
            WHERE user_id = ? AND report_id = ?
            ORDER BY timestamp
            """, (user_id, report_id))
        else:
            cursor.execute("""
            SELECT timestamp, role, message
            FROM chat_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 50
            """, (user_id,))
        
        columns = [desc[0] for desc in cursor.description]
        history = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return history
    
    def clear_chat_history(self, user_id: str, report_id: int = None):
        """Clear chat history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if report_id:
            cursor.execute("DELETE FROM chat_history WHERE user_id = ? AND report_id = ?", (user_id, report_id))
        else:
            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()

# ============== Q&A AGENT (COMPLETE) ==============

class MedicalQAAgent:
    def __init__(self, db: MedicalDatabase, user_id: str):
        self.db = db
        self.user_id = user_id
        self.llm = llm
    
    def get_context(self, report_id: int = None) -> str:
        """Build comprehensive context from user's medical history."""
        context = []
        
        user_profile = self.db.get_user_profile(self.user_id)
        if user_profile:
            context.append("Patient Profile:")
            if user_profile.get('date_of_birth'):
                from datetime import datetime
                dob = datetime.strptime(user_profile['date_of_birth'], '%Y-%m-%d')
                age = (datetime.now() - dob).days // 365
                context.append(f"- Age: {age} years")
            if user_profile.get('gender'):
                context.append(f"- Gender: {user_profile['gender']}")
            context.append("")
        
        if report_id:
            report = self.db.get_report_details(report_id)
            context.append(f"Current Report Analysis (Date: {report['report_date'][:10]}):")
            context.append(f"\nExecutive Summary:\n{report['summary']}")
            context.append(f"\nRecommendations:\n{report['recommendations']}")
            context.append(f"\nDetailed Test Results:")
            
            normal_tests = []
            abnormal_tests = []
            
            for test in report['test_results']:
                test_info = f"- {test['test_name']}: {test['test_value']} {test['units']}"
                if test['reference_range']:
                    test_info += f" (Normal: {test['reference_range']})"
                if test['status']:
                    test_info += f" [Status: {test['status'].upper()}]"
                if test.get('analysis'):
                    test_info += f"\n  Analysis: {test['analysis']}"
                
                if test['status'] in ['high', 'low']:
                    abnormal_tests.append(test_info)
                else:
                    normal_tests.append(test_info)
            
            if abnormal_tests:
                context.append("\nAbnormal Tests (Need Attention):")
                context.extend(abnormal_tests)
            
            if normal_tests:
                context.append("\nNormal Tests:")
                context.extend(normal_tests[:5])
                if len(normal_tests) > 5:
                    context.append(f"... and {len(normal_tests) - 5} more normal tests")
        else:
            reports = self.db.get_user_reports(self.user_id)
            if reports:
                context.append("Medical History Overview:")
                context.append(f"Total Reports: {len(reports)}")
                context.append("\nRecent Reports:")
                for i, report in enumerate(reports[:3], 1):
                    context.append(
                        f"{i}. {report['report_date'][:10]}: "
                        f"{report['total_tests']} tests "
                        f"({report['normal_count']} normal, {report['abnormal_count']} abnormal)"
                    )
        
        return "\n".join(context)
    
    def answer_question(self, question: str, report_id: int = None) -> str:
        """Answer medical questions with enhanced accuracy and context."""
        context = self.get_context(report_id)
        
        prompt = f"""
You are an expert medical assistant with extensive knowledge in laboratory medicine.

PATIENT'S MEDICAL CONTEXT:
{context}

PATIENT'S QUESTION: {question}

IMPORTANT GUIDELINES:
1. **Accuracy First**: Provide medically accurate information
2. **Context-Aware**: Reference specific test results when relevant
3. **Clear Communication**: Explain medical terms in simple language
4. **Personalized**: Consider the patient's medical history
5. **Actionable**: Provide specific, actionable advice when appropriate
6. **Safety**: Always remind to consult healthcare provider for medical decisions
7. **Empathetic**: Be reassuring and supportive while being honest

ANSWER:
"""
        
        response = self.llm.invoke(prompt)
        return response.content


# Add this code RIGHT AFTER the MedicalQAAgent class and BEFORE show_main_app()

# ============== INITIALIZE SERVICES ==============

# Initialize services
db = MedicalDatabase()
email_service = EmailService()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'current_report_id' not in st.session_state:
    st.session_state.current_report_id = None
if 'auth_stage' not in st.session_state:
    st.session_state.auth_stage = 'login'
if 'pending_email' not in st.session_state:
    st.session_state.pending_email = None
if 'pending_user_data' not in st.session_state:
    st.session_state.pending_user_data = None

# ADD THESE NEW LINES HERE:
if 'verification_success' not in st.session_state:
    st.session_state.verification_success = False
if 'password_reset_complete' not in st.session_state:
    st.session_state.password_reset_complete = False
if 'reset_stage' not in st.session_state:
    st.session_state.reset_stage = 'request'
if 'page' not in st.session_state:
    st.session_state.page = '📊 Dashboard'
if 'view_report_modal' not in st.session_state:
    st.session_state.view_report_modal = False


# for view details in history section
if 'show_report_details' not in st.session_state:
    st.session_state.show_report_details = False


# ============== VALIDATION FUNCTIONS ==============

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"

# ============== AUTHENTICATION PAGES ==============

def show_login_page():
    """Professional login page with modern design."""
    
    # Hero Section
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 3rem;">
        <h1>Medical Analysis Agent</h1>
        <p>Your Intelligent Medical Report Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="auth-header">
            <h2>Welcome Back</h2>
            <p>Sign in to access your health dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email Address", placeholder="Enter you email address", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            
            remember_me = st.checkbox("Remember me")
            
            col_a, col_b = st.columns(2)
            with col_a:
                submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            with col_b:
                forgot = st.form_submit_button("Forgot Password", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please fill in all fields")
                elif not validate_email(email):
                    st.error("Please enter a valid email address")
                else:
                    with st.spinner("Authenticating..."):
                        user_info = db.authenticate_user(email, password)
                        
                        if user_info:
                            if not user_info['is_verified']:
                                st.warning("Please verify your email first")
                                st.session_state.pending_email = email
                                st.session_state.auth_stage = 'verify_email'
                                st.rerun()
                            else:
                                st.session_state.logged_in = True
                                st.session_state.user_info = user_info
                                st.success(f"Welcome back, {user_info['full_name']}!")
                                st.balloons()
                                st.rerun()
                        else:
                            st.error("Invalid credentials. Account may be locked after 5 failed attempts.")
            
            if forgot:
                st.session_state.auth_stage = 'forgot_password'
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <p style="color: #666; margin-bottom: 1rem;">New to Medical Analysis Agent?</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Create New Account", use_container_width=True, key="goto_signup"):
            st.session_state.auth_stage = 'signup'
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Features Section
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin: 4rem 0 2rem 0;">
        <h2 style="color: #333; font-size: 2rem; font-weight: 700;">Why Choose Medical Analysis Agent?</h2>
        <p style="color: #666; font-size: 1.1rem;">Understand your health like never before</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    features = [
        ("📤", "Upload Reports", "Simply upload your medical reports in PDF format"),
        ("🤖", "AI Analysis", "Get instant AI-powered insights and explanations"),
        ("📊", "Track Trends", "Monitor your health metrics over time"),
        ("💬", "Ask Questions", "Chat with AI about your health data 24/7")
    ]
    
    for col, (icon, title, desc) in zip([col1, col2, col3, col4], features):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{title}</div>
                <div class="feature-description">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


def show_signup_page():
    """Professional signup page."""
    
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 3rem;">
        <h1>Medical Analysis Agent</h1>
        <p>Join thousands of users taking control of their health</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="auth-header">
            <h2>Create Your Account</h2>
            <p>Start your health journey today</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("signup_form"):
            full_name = st.text_input("Full Name *", placeholder="Enter your name")
            email = st.text_input("Email Address *", placeholder="Enter your email address")
            
            col_a, col_b = st.columns(2)
            with col_a:
                password = st.text_input("Password *", type="password", placeholder="Create password")
            with col_b:
                confirm_password = st.text_input("Confirm Password *", type="password", placeholder="Re-enter password")
            
            with st.expander("Optional Information (helps personalize your experience)"):
                col_c, col_d = st.columns(2)
                with col_c:
                    dob = st.date_input("Date of Birth", value=None, max_value=datetime.now())
                with col_d:
                    gender = st.selectbox("Gender", ["", "Male", "Female", "Other", "Prefer not to say"])
                
                phone = st.text_input("Phone Number", placeholder="+1234567890")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            agree = st.checkbox("I agree to the **Terms of Service** and **Privacy Policy** *")
            
            submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            
            if submit:
                if not all([full_name, email, password, confirm_password]):
                    st.error("Please fill in all required fields (*)")
                elif not validate_email(email):
                    st.error("Please enter a valid email address")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    is_valid, msg = validate_password(password)
                    if not is_valid:
                        st.error(f"{msg}")
                    elif not agree:
                        st.error("Please agree to the Terms of Service and Privacy Policy")
                    else:
                        with st.spinner("Creating your account..."):
                            success, result = db.create_user(
                                email, password, full_name,
                                str(dob) if dob else None,
                                gender if gender else None,
                                phone if phone else None
                            )
                            
                            if success:
                                # Generate OTP
                                otp = db.create_otp(email, "verification")
                                
                                # Try to send OTP (will print to console if email not configured)
                                email_sent = email_service.send_otp(email, otp, "verification")
                                
                                # Store data and redirect to verification
                                st.session_state.pending_email = email
                                st.session_state.pending_user_data = {'full_name': full_name}
                                st.session_state.auth_stage = 'verify_email'
                                st.rerun()
                            else:
                                st.error(f"Error: {result}")
        
        st.markdown("---")
        
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <p style="color: #666; margin-bottom: 1rem;">Already have an account?</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Sign In Instead", use_container_width=True):
            st.session_state.auth_stage = 'login'
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


def show_verify_email_page():
    """Professional email verification page."""
    
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 3rem;">
        <h1>Verify Your Email</h1>
        <p>Enter the verification code to activate your account</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Check for success flag first
        if st.session_state.get('verification_success'):
            st.success("Email verified successfully!")
            st.markdown("""
            <div class="alert-box alert-success">
                <strong>Success!</strong><br>
                Your account is now active. Redirecting to login...
            </div>
            """, unsafe_allow_html=True)
            
            # Clear flags
            st.session_state.verification_success = False
            st.session_state.pending_email = None
            st.session_state.pending_user_data = None
            st.session_state.auth_stage = 'login'
            
            # Auto redirect
            import time
            time.sleep(2)
            st.rerun()
            return  # Exit function
        
        # Check if email is configured
        if os.getenv('SMTP_USERNAME'):
            st.markdown(f"""
            <div class="alert-box alert-info">
                <strong>Check Your Email</strong><br>
                We've sent a 6-digit verification code to:<br>
                <strong style="font-size: 1.1rem; color: #667eea;">{st.session_state.pending_email}</strong>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-box alert-warning">
                <strong>Development Mode - Check Console</strong><br>
                Your verification code has been printed to the terminal/console where Streamlit is running.<br><br>
                Look for:<br>
                <code style="background: #f5f5f5; padding: 0.5rem; border-radius: 4px; display: block; margin-top: 0.5rem;">
                OTP Code: XXXXXX
                </code>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("**Email not configured.** To enable email delivery, set up SMTP credentials in your `.env` file.")
        
        with st.form("verify_form"):
            otp = st.text_input(
                "Enter 6-Digit Verification Code",
                max_chars=6,
                placeholder="000000",
                help="Enter the 6-digit code from your email or console",
                key="verify_otp"
            )
            
            submit = st.form_submit_button("Verify Email", use_container_width=True, type="primary")
            
            if submit:
                if len(otp) != 6 or not otp.isdigit():
                    st.error("Please enter a valid 6-digit code")
                else:
                    with st.spinner("Verifying..."):
                        if db.verify_otp(st.session_state.pending_email, otp, "verification"):
                            db.verify_user_account(st.session_state.pending_email)
                            
                            # Try to send welcome email
                            if st.session_state.pending_user_data:
                                try:
                                    email_service.send_welcome_email(
                                        st.session_state.pending_email,
                                        st.session_state.pending_user_data.get('full_name', 'User')
                                    )
                                except:
                                    pass
                            
                            # st.balloons()
                            
                            # Set success flag to trigger redirect
                            st.session_state.verification_success = True
                            st.rerun()
                        else:
                            st.error("Invalid or expired verification code")
                            st.info("Codes expire after 10 minutes. You can request a new one below.")
        
        st.markdown("---")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Resend Code", use_container_width=True):
                otp = db.create_otp(st.session_state.pending_email, "verification")
                email_service.send_otp(st.session_state.pending_email, otp, "verification")
                
                if os.getenv('SMTP_USERNAME'):
                    st.success("New code sent to your email!")
                else:
                    st.success("New code generated! Check your console/terminal.")
                st.rerun()
        
        with col_b:
            if st.button("Back to Login", use_container_width=True):
                st.session_state.auth_stage = 'login'
                st.rerun()


def show_forgot_password_page():
    """Professional password reset page."""
    
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 3rem;">
        <h1>Reset Password</h1>
        <p>Don't worry, we'll help you get back in</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        if 'reset_stage' not in st.session_state:
            st.session_state.reset_stage = 'request'
        
        if st.session_state.reset_stage == 'request':
            st.markdown("""
            <div class="auth-header">
                <h2>Password Recovery</h2>
                <p>Enter your email to receive a reset code</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("forgot_password_form"):
                email = st.text_input("Email Address", placeholder="Enter you email address")
                submit = st.form_submit_button("Send Reset Code", use_container_width=True, type="primary")
                
                if submit:
                    if not email or not validate_email(email):
                        st.error("Please enter a valid email address")
                    else:
                        with st.spinner("Sending reset code..."):
                            otp = db.create_otp(email, "password_reset")
                            if email_service.send_otp(email, otp, "password reset"):
                                st.success("Reset code sent to your email!")
                                st.session_state.pending_email = email
                                st.session_state.reset_stage = 'verify'
                                st.rerun()
                            else:
                                st.error("Failed to send email. Please try again.")
            
            st.markdown("---")
            
            if st.button("Back to Login", use_container_width=True):
                st.session_state.auth_stage = 'login'
                st.session_state.reset_stage = 'request'
                st.rerun()
        
        elif st.session_state.reset_stage == 'verify':
            st.markdown(f"""
            <div class="alert-box alert-info">
                <strong>Check Your Email</strong><br>
                Reset code sent to: <strong>{st.session_state.pending_email}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("verify_reset_form"):
                otp = st.text_input("Enter Reset Code", max_chars=6, placeholder="000000")
                submit = st.form_submit_button("Verify Code", use_container_width=True, type="primary")
                
                if submit:
                    if len(otp) != 6 or not otp.isdigit():
                        st.error("Please enter a valid 6-digit code")
                    else:
                        if db.verify_otp(st.session_state.pending_email, otp, "password_reset"):
                            st.success("Code verified! Set your new password.")
                            st.session_state.reset_stage = 'reset'
                            st.rerun()
                        else:
                            st.error("Invalid or expired code")
            
            if st.button("Resend Code", use_container_width=True):
                otp = db.create_otp(st.session_state.pending_email, "password_reset")
                if email_service.send_otp(st.session_state.pending_email, otp, "password reset"):
                    st.success("New code sent!")
            
            st.markdown("---")
            
            if st.button("Back to Login", use_container_width=True, key="back_verify"):
                st.session_state.auth_stage = 'login'
                st.session_state.reset_stage = 'request'
                st.session_state.pending_email = None
                st.rerun()
        
        elif st.session_state.reset_stage == 'reset':
            # Check for success flag first
            if st.session_state.get('password_reset_complete'):
                st.success("Password reset successfully!")
                st.markdown("""
                <div class="alert-box alert-success">
                    <strong>Success!</strong><br>
                    Your password has been reset. Redirecting to login...
                </div>
                """, unsafe_allow_html=True)
                
                # Clear all flags
                st.session_state.password_reset_complete = False
                st.session_state.reset_stage = 'request'
                st.session_state.pending_email = None
                st.session_state.auth_stage = 'login'
                
                import time
                time.sleep(2)
                st.rerun()
                return
            
            st.markdown("""
            <div class="auth-header">
                <h2>Create New Password</h2>
                <p>Choose a strong password for your account</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("reset_password_form"):
                new_password = st.text_input("New Password", type="password", placeholder="Create new password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                submit = st.form_submit_button("Reset Password", use_container_width=True, type="primary")
                
                if submit:
                    if not new_password or not confirm_password:
                        st.error("Please fill in all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        is_valid, msg = validate_password(new_password)
                        if not is_valid:
                            st.error(f"{msg}")
                        else:
                            if db.reset_password(st.session_state.pending_email, new_password):
                                st.balloons()
                                # Set success flag
                                st.session_state.password_reset_complete = True
                                st.rerun()
                            else:
                                st.error("Failed to reset password")
            
            st.markdown("---")
            
            if st.button("Back to Login", use_container_width=True, key="back_reset"):
                st.session_state.auth_stage = 'login'
                st.session_state.reset_stage = 'request'
                st.session_state.pending_email = None
                st.rerun()

# ============== MAIN APPLICATION PAGES ==============

def show_main_app():
    """Display main application interface with modern sidebar."""
    user_id = st.session_state.user_info['user_id']
    
    # Modern Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 0 0 1.5rem; border-bottom: 2px solid rgba(255,255,255,0.2); margin-bottom: 1.5rem;">
            <h2 style="margin: 0; font-size: 1.5rem;">Medical Analysis Agent</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">Your Health Dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        # User Profile Section
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                <div style="background: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 0.75rem;">
                    <span style="color: #667eea; font-size: 1.2rem; font-weight: 700;">
                        {st.session_state.user_info['full_name'][0].upper()}
                    </span>
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; font-size: 1rem;">{st.session_state.user_info['full_name']}</div>
                    <div style="opacity: 0.8; font-size: 0.75rem;">{st.session_state.user_info['email']}</div>
                </div>
            </div>
            {'<div style="text-align: center; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.2);"><span style="background: #28a745; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem;">✓ Verified</span></div>' if st.session_state.user_info['is_verified'] else '<div style="text-align: center; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.2);"><span style="background: #ffc107; color: #333; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem;">⚠ Not Verified</span></div>'}
        </div>
        """, unsafe_allow_html=True)

        # Professional Navigation Menu
        st.markdown("### Navigation")
        
        # Initialize page in session state if not exists
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'Dashboard'
        
        # Navigation items
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Upload Report", "upload"),
            ("Ask Questions", "questions"),
            ("Health Trends", "trends"),
            ("History", "history"),
            ("Settings", "settings")
        ]
        
        # Custom CSS for navigation buttons
        st.markdown("""
        <style>
        .nav-button {
            width: 100%;
            padding: 0.75rem 1rem;
            margin: 0.25rem 0;
            border: none;
            border-radius: 10px;
            background: rgba(255,255,255,0.05);
            color: white;
            text-align: left;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            text-decoration: none;
        }
        
        .nav-button:hover {
            background: rgba(255,255,255,0.15);
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .nav-button.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            font-weight: 600;
        }
        
        .nav-button-icon {
            margin-right: 0.75rem;
            font-size: 1.1rem;
        }
        
        /* Hide default Streamlit button styling */
        .stButton > button {
            width: 100%;
            padding: 0.75rem 1rem;
            margin: 0.25rem 0;
            border: none;
            border-radius: 10px;
            background: rgba(255,255,255,0.05);
            color: white;
            text-align: left;
            font-size: 0.95rem;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background: rgba(255,255,255,0.15);
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            color: white;
            border: none;
        }
        
        .stButton > button:active,
        .stButton > button:focus {
            background: rgba(255,255,255,0.15);
            color: white;
            border: none;
            box-shadow: none;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create navigation buttons
        for display_name, page_id in nav_items:
            is_active = st.session_state.current_page == display_name
            button_class = "active" if is_active else ""
            
            # Use columns to create custom button appearance
            col1, col2 = st.columns([0.95, 0.05])
            with col1:
                if st.button(
                    display_name,
                    key=f"nav_{page_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.current_page = display_name
                    st.rerun()
        
        st.markdown("---")
        
        # Recent Reports
        # st.markdown("### Recent Reports")
        # recent_reports = db.get_user_reports(user_id)[:3]
        
        # if recent_reports:
        #     for report in recent_reports:
        #         with st.expander(f"{report['report_date'][:10]}", expanded=False):
        #             st.markdown(f"""
        #             <div style="font-size: 0.85rem;">
        #                 <strong>Tests:</strong> {report['total_tests']}<br>
        #                 <strong>Normal:</strong> {report['normal_count']}<br>
        #                 <strong>Abnormal:</strong> {report['abnormal_count']}
        #             </div>
        #             """, unsafe_allow_html=True)
        #             if st.button("View Details", key=f"view_{report['id']}", use_container_width=True):
        #                 st.session_state.current_report_id = report['id']
        #                 st.rerun()
        # else:
        #     st.info("No reports yet! Upload your first report to get started.")
        
        # st.markdown("---")
        
        # Logout Button
        if st.button("Logout", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.session_state.current_report_id = None
            st.rerun()
        
        st.markdown("""
        <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.2); text-align: center; font-size: 0.75rem; opacity: 0.7;">
            <p>Version 1.0.0</p>
            <p>© 2024 Medical Analysis Agent</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main Content Area - use current_page from session state
    current_page = st.session_state.current_page
    
    if current_page == "Dashboard":
        show_dashboard_page(user_id)
    elif current_page == "Upload Report":
        show_upload_page(user_id)
    elif current_page == "Ask Questions":
        show_qa_page(user_id)
    elif current_page == "Health Trends":
        show_trends_page(user_id)
    elif current_page == "History":
        show_history_page(user_id)
    elif current_page == "Settings":
        show_settings_page(user_id)


def show_dashboard_page(user_id: str):
    """Modern dashboard with health overview."""
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 2rem;">
        <h1>Health Dashboard</h1>
        <p>Your comprehensive health overview at a glance</p>
    </div>
    """, unsafe_allow_html=True)
    
    reports = db.get_user_reports(user_id)
    
    if not reports:
        st.markdown("""
        <div class="modern-card" style="text-align: center; padding: 2rem 2rem;">
            <h2 style="color: #667eea; margin-bottom: 1rem;">No Reports Yet</h2>
            <p style="color: #666; font-size: 1.1rem;">
                Upload your first medical report to see your health insights here
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1,col2,col3 = st.columns([1,2,1])
        with col2:
            if st.button("Upload Your First Report", type="primary", use_container_width=True):
                st.session_state.current_page = "Upload Report"
                st.rerun()
    else:
        # Statistics Cards
        col1, col2, col3, col4 = st.columns(4)
        
        total_tests = sum(r['total_tests'] for r in reports)
        total_normal = sum(r['normal_count'] for r in reports)
        total_abnormal = sum(r['abnormal_count'] for r in reports)
        latest = reports[0]
        
        with col1:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #550055 0%, #bb66aa 100%);">
                <div class="stat-label">Total Reports</div>
                <div class="stat-value">{len(reports)}</div>
                <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.9;">All Time</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card" style="background:linear-gradient(135deg, #162a80 0%, #5a7fcf 100%);">
                <div class="stat-label">Total Tests</div>
                <div class="stat-value">{total_tests}</div>
                <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.9;">Analyzed</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            normal_pct = (total_normal / total_tests * 100) if total_tests > 0 else 0
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%);">
                <div class="stat-label">Normal Tests</div>
                <div class="stat-value">{total_normal}</div>
                <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.9;">{normal_pct:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);">
                <div class="stat-label">Abnormal Tests</div>
                <div class="stat-value">{total_abnormal}</div>
                <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.9;">Need Attention</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Latest Report Summary
        st.markdown("### Latest Report Summary")
        
        latest_details = db.get_report_details(latest['id'])
        
        # First Row - Quick Stats (Full Width)
        st.markdown("""
        <div class="modern-card">
            <h4 style="color: #667eea;">Quick Stats</h4>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Tests", latest['total_tests'])
        with col2:
            st.metric("Normal", latest['normal_count'])
        with col3:
            st.metric("Abnormal", latest['abnormal_count'])
        
        # View Full Report Button in new row
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("View Full Report", use_container_width=True, type="primary", key="view_full_dashboard"):
                st.session_state.current_report_id = latest['id']
                st.session_state.current_page = "History"
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Second Row - Report Info (Full Width)
        st.markdown(f"""
        <div class="modern-card">
            <h4 style="color: #667eea; margin-bottom: 1rem;">Report from {latest['report_date'][:10]}</h4>
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                <strong>Filename:</strong> {latest['filename']}<br>
                <strong>Total Tests:</strong> {latest['total_tests']}<br>
                <strong>Normal:</strong> {latest['normal_count']}<br>
                <strong>Abnormal:</strong> {latest['abnormal_count']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Initialize toggle state in session state
        if 'show_summary' not in st.session_state:
            st.session_state.show_summary = False

        # Third Row - Summary & Recommendations Toggle Button (Full Width)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Change button text based on state
            button_text = "Hide Summary & Recommendations" if st.session_state.show_summary else "View Summary & Recommendations"
            button_icon = "▼" if st.session_state.show_summary else "▶"
            
            if st.button(f"{button_icon} {button_text}", use_container_width=True, type="secondary", key="view_summary"):
                # Toggle the state
                st.session_state.show_summary = not st.session_state.show_summary
                st.rerun()

        # Show/hide summary based on toggle state
        if st.session_state.show_summary:  
            st.markdown("<br>", unsafe_allow_html=True)

            # Debug: Show raw content
            # with st.expander("🔍 Debug - View Raw Data", expanded=False):
            #     st.write("**Raw Summary Content:**")
            #     st.code(latest_details['summary'])
            #     st.write("**Raw Recommendations Content:**")
            #     st.code(latest_details['recommendations'])
            
            # to render markdown properly into html
            import markdown

            # Convert markdown to HTML, extension for extra support of tables,newlines etc
            summary_html = markdown.markdown(
                latest_details['summary'],
                extensions=['extra', 'nl2br']
            )
            recommendations_html = markdown.markdown(
                latest_details['recommendations'],
                extensions=['extra', 'nl2br']
            )

            st.markdown(f"""
            <div class="modern-card">
                <h3 style="color: #667eea; font-size: 1.5rem; font-weight: 700;">
                    Summary
                </h3>
                <div class="summary-box-style">
                    {summary_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown(f"""
            <div class="modern-card">
                <h3 style="color: #667eea; font-size: 1.5rem; font-weight: 700;">
                    Key Recommendations
                </h3>
                <div class="recommendation-box-style">
                    {recommendations_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # with st.expander("Executive Summary", expanded=True):
            #     st.markdown(f"""
            #     <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 1.5rem; border-radius: 12px; line-height: 1.8; font-size: 1rem; color: #333;">
            #     {summary_html}
            #     </div>
            #     """, unsafe_allow_html=True)
            
            # with st.expander("Key Recommendations", expanded=True):
            #     st.markdown(f"""
            #     <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffe5a0 100%); padding: 1.5rem; border-radius: 12px; line-height: 1.8; font-size: 1rem; color: #856404;">
            #     {recommendations_html}
            #     </div>
            #     """, unsafe_allow_html=True)
            
        # Test Results Trend
        if len(reports) > 1:
            st.markdown("### Test Results Trend")
            
            all_tests = set()
            for report in reports:
                report_details = db.get_report_details(report['id'])
                for test in report_details['test_results']:
                    all_tests.add(test['test_name'])
            
            if all_tests:
                selected_test = st.selectbox(
                    "Select test to view trend:",
                    sorted(all_tests),
                    key="dashboard_test_select"
                )
                
                trends = db.get_test_trends(user_id, selected_test)
                
                if len(trends) > 1:
                    df_trends = pd.DataFrame(trends)
                    df_trends['report_date'] = pd.to_datetime(df_trends['report_date'])
                    df_trends['test_value'] = pd.to_numeric(df_trends['test_value'], errors='coerce')
                    
                    fig = px.line(
                        df_trends,
                        x='report_date',
                        y='test_value',
                        title=f'{selected_test} Trend Over Time',
                        markers=True
                    )
                    
                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title=f"{selected_test} ({trends[0]['units']})",
                        hovermode='x unified',
                        plot_bgcolor='white',
                        paper_bgcolor='white'
                    )
                    
                    fig.update_traces(
                        line=dict(color='#667eea', width=3),
                        marker=dict(size=10, color='#764ba2')
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)


def show_upload_page(user_id: str):
    """Modern upload page with drag-and-drop."""
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 2rem;">
        <h1>Upload Medical Report</h1>
        <p>Get instant AI-powered analysis of your lab results</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features Section
    col1, col2, col3, col4 = st.columns(4)
    
    features = [
        ("📄", "PDF Support", "Upload lab reports"),
        ("🤖", "AI Analysis", "Instant intelligent analysis"),
        ("📊", "Visual Reports", "Easy-to-understand charts"),
        ("💾", "Auto Save", "Reports saved automatic")
    ]
    
    for col, (icon, title, desc) in zip([col1, col2, col3, col4], features):
        with col:
            st.markdown(f"""
            <div class="modern-card" style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #eaf3ff 0%, #d4e5ff 100%);">
                <div style="font-weight: 600; color: #333; margin-bottom: 0.25rem;">{title}</div>
                <div style="font-size: 0.85rem; color: #666;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Upload Section
    st.markdown("""
    <div class="modern-card">
        <h3 style="color: #667eea;">Upload Your Report</h3>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload your lab report in PDF format (max 10MB)",
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        st.success(f"File selected: **{uploaded_file.name}**")
        
        # File details section
        st.markdown(f"""
        <div class="alert-box alert-info">
            <strong>File Details</strong><br>
            <strong>Name:</strong> {uploaded_file.name}<br>
            <strong>Size:</strong> {uploaded_file.size / 1024:.2f} KB<br>
            <strong>Type:</strong> {uploaded_file.type}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Analyze button on new line, centered
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            analyze_button = st.button("Analyze Report", type="primary", use_container_width=True)
        
        if analyze_button:
            # Save file
            upload_dir = Path("uploads")
            upload_dir.mkdir(exist_ok=True)
            
            file_path = upload_dir / f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Analysis with progress
            st.markdown("""
            <div class="modern-card" style="margin-top: 2rem;">
                <h4 style="color: #667eea;">Analyzing Your Report...</h4>
            </div>
            """, unsafe_allow_html=True)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Parse PDF
                status_text.markdown("**Step 1/4:** Parsing PDF document...")
                progress_bar.progress(25)
                
                inputs = {"pdf_path": str(file_path)}
                
                # Step 2: Extract data
                status_text.markdown("**Step 2/4:** Extracting medical data...")
                progress_bar.progress(50)
                
                final_state = analyzer_workflow.invoke(inputs)
                
                # Step 3: Analyze results
                status_text.markdown("**Step 3/4:** Analyzing test results...")
                progress_bar.progress(75)
                
                output = generate_user_friendly_output(final_state)
                
                # Step 4: Generate report
                status_text.markdown("**Step 4/4:** Generating report...")
                progress_bar.progress(90)
                
                if output['success']:
                    pdf_dir = Path("reports")
                    pdf_dir.mkdir(exist_ok=True)
                    pdf_path = pdf_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    
                    generate_pdf_report(output, str(pdf_path))
                    
                    report_id = db.save_report(
                        user_id,
                        output,
                        uploaded_file.name,
                        str(pdf_path)
                    )
                    
                    st.session_state.current_report_id = report_id
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    progress_bar.empty()
                    
                    st.success("Report analyzed successfully!")
                    
                    # Display Results
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Results Header
                    st.markdown("""
                    <div style="text-align: center; margin: 2rem 0;">
                        <h2 style="color: #667eea; font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem;">
                            Analysis Results
                        </h2>
                        <p style="color: #666; font-size: 1.1rem;">Your comprehensive health report is ready</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Statistics Cards
                    stats = output['statistics']
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.markdown(f"""
                        <div class="stat-card" style="min-height: 180px;">
                            <div class="stat-label">Total Tests</div>
                            <div class="stat-value">{stats['total_tests']}</div>
                            <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.9;">Analyzed</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); min-height: 180px;">
                            <div class="stat-label">Normal</div>
                            <div class="stat-value">{stats['normal_count']}</div>
                            <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.9;">Healthy</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%); min-height: 180px;">
                            <div class="stat-label">Abnormal</div>
                            <div class="stat-value">{stats['abnormal_count']}</div>
                            <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.9;">Attention</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col4:
                        st.markdown(f"""
                        <div class="stat-card" style="background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%); min-height: 180px;">
                            <div class="stat-label">No Reference</div>
                            <div class="stat-value">{stats['no_reference_count']}</div>
                            <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.9;">Data Only</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    
                    # Summary and Recommendations
                    import markdown
                    # Convert markdown to HTML
                    summary_html = markdown.markdown(
                        output['summary'],
                        extensions=['extra', 'nl2br']
                    )
                    recommendations_html = markdown.markdown(
                        output['recommendations'],
                        extensions=['extra', 'nl2br']
                    )

                    st.markdown(f"""
                    <div class="modern-card">
                        <h3 style="color: #667eea; font-size: 1.5rem; font-weight: 700;">
                            Summary
                        </h3>
                        <div class="summary-box-style">
                            {summary_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    st.markdown(f"""
                    <div class="modern-card">
                        <h3 style="color: #667eea; font-size: 1.5rem; font-weight: 700;">
                            Key Recommendations
                        </h3>
                        <div class="recommendation-box-style">
                            {recommendations_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Abnormal Tests Section
                    abnormal = [r for r in output['detailed_results'] if r['status'] in ['high', 'low']]
                    
                    if abnormal:
                        st.markdown("""
                        <div style="margin: 2rem 0 1.5rem 0;">
                            <h3 style="color: #dc3545; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;">
                                Tests Requiring Attention
                            </h3>
                            <p style="color: #666; font-size: 1rem;">
                                These results are outside the normal range and may need follow-up
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display abnormal tests
                        for i in range(0, len(abnormal), 2):
                            cols = st.columns(2)
                            
                            for idx in range(2):
                                if i + idx < len(abnormal):
                                    result = abnormal[i + idx]
                                    status_emoji = "📈" if result['status'] == 'high' else "📉"
                                    status_color = "#dc3545" if result['status'] == 'high' else "#ffc107"
                                    status_bg = "#f8d7da" if result['status'] == 'high' else "#fff3cd"
                                    
                                    with cols[idx]:
                                        st.markdown(f"""
                                        <div class="modern-card" style="border-left: 4px solid {status_color}; background: {status_bg}; min-height: 220px;">
                                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                                                <h4 style="color: #333; margin: 0; font-size: 1.2rem; flex: 1;">
                                                    {status_emoji} {result['test_name']}
                                                </h4>
                                                <span class="test-status status-{result['status']}" style="margin-left: 1rem;">
                                                    {result['status'].upper()}
                                                </span>
                                            </div>
                                            <div style="background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                                                <div style="display: grid; grid-template-columns: auto 1fr; gap: 0.5rem 1rem; font-size: 0.95rem;">
                                                    <strong style="color: #666;">Value:</strong>
                                                    <span style="color: {status_color}; font-weight: 700; font-size: 1.1rem;">
                                                        {result['test_value']} {result['units']}
                                                    </span>
                                                    <strong style="color: #666;">Normal Range:</strong>
                                                    <span style="color: #333;">{result['reference_range']}</span>
                                                </div>
                                            </div>
                                            {f'<div style="background: white; padding: 1rem; border-radius: 8px; font-size: 0.9rem; line-height: 1.6; color: #555;"><strong>Analysis:</strong><br>{result.get("analysis", "")}</div>' if result.get('analysis') else ''}
                                        </div>
                                        """, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Download Section
                    st.markdown("---")
                    st.markdown("""
                    <div style="text-align: center; margin: 2rem 0 1rem 0;">
                        <h3 style="color: #667eea; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">
                            Download Your Report
                        </h3>
                        <p style="color: #666; font-size: 1rem;">
                            Get a comprehensive PDF report with all your test results and analysis
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Center the download button
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        with open(pdf_path, 'rb') as f:
                            st.download_button(
                                label="Download Full Report (PDF)",
                                data=f,
                                file_name=f"medical_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary"
                            )
                    
                    # st.markdown("<br>", unsafe_allow_html=True)
                    
                    # # Action buttons - FIXED KEYS HERE
                    # col1, col2, col3 = st.columns(3)
                    
                    # with col1:
                    #     if st.button("View Dashboard", use_container_width=True, type="secondary", key="upload_nav_dashboard"):
                    #         st.session_state.current_page = 'Dashboard'
                    #         st.rerun()
                    
                    # with col2:
                    #     if st.button("Ask Questions", use_container_width=True, type="secondary", key="upload_nav_questions"):
                    #         st.session_state.current_page = 'Ask Questions'
                    #         st.rerun()
                    
                    # with col3:
                    #     if st.button("Upload Another", use_container_width=True, type="secondary", key="upload_another"):
                    #         st.rerun()
                
                else:
                    st.error(f"Error: {output['details']}")
                    st.info(output['suggestion'])
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                import traceback
                with st.expander("View Error Details"):
                    st.code(traceback.format_exc())


def show_qa_page(user_id: str):
    """Modern Q&A page with chat interface."""
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 2rem;">
        <h1>Ask Your Medical Assistant</h1>
        <p>Get personalized answers about your health reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    reports = db.get_user_reports(user_id)
    
    if not reports:
        st.markdown("""
        <div class="modern-card" style="text-align: center; padding: 3rem;">
            <h3 style="color: #667eea;">No Reports Available</h3>
            <p style="color: #666; margin: 1rem 0;">Upload a medical report first to start asking questions</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1,col2,col3 = st.columns([1,2,1])
        with col2:
            if st.button("Upload Report", type="primary",use_container_width=True):
                st.rerun()
            return
    
    # Report Selection
    # col1, col2 = st.columns([3, 1])
    
    report_options = {
        "All Reports (General Questions)": None,
        **{f"📄 {r['report_date'][:10]} - {r['filename']}": r['id'] for r in reports}
    }
    
    selected_report = st.selectbox(
        "Select context for your questions:",
        options=list(report_options.keys()),
        key="qa_report_select"
    )
    
    # Example Questions
    with st.expander("Example Questions You Can Ask"):
        st.markdown("""
        <div style="columns: 2; column-gap: 2rem; padding: 1rem;">
            <div style="margin-bottom: 1rem;">
                <strong>About Your Results:</strong>
                <ul style="margin-top: 0.5rem;">
                    <li>What do my recent test results mean?</li>
                    <li>Explain my cholesterol levels</li>
                    <li>Are any of my results concerning?</li>
                </ul>
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Trends & History:</strong>
                <ul style="margin-top: 0.5rem;">
                    <li>How has my blood sugar changed?</li>
                    <li>Show improvements over time</li>
                    <li>Compare my last two reports</li>
                </ul>
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Health Advice:</strong>
                <ul style="margin-top: 0.5rem;">
                    <li>What should I do about high cholesterol?</li>
                    <li>Diet recommendations for my condition</li>
                    <li>When should I see a doctor?</li>
                </ul>
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Understanding Terms:</strong>
                <ul style="margin-top: 0.5rem;">
                    <li>What is HbA1c?</li>
                    <li>Explain thyroid function tests</li>
                    <li>What does elevated CRP mean?</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # st.markdown("<br>", unsafe_allow_html=True)

    # clear chat section
    report_id = report_options[selected_report]

    col1,col2,col3 = st.columns([3,2,3])
    with col2:
        if st.button("Clear Chat", use_container_width=True):
            db.clear_chat_history(user_id, report_id if report_id else None)
            st.success("Chat cleared!")
            st.rerun()

    
    # Chat Container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Initialize QA Agent
    qa_agent = MedicalQAAgent(db, user_id)
    
    # Display Chat History
    chat_history = db.get_chat_history(user_id, report_id)
    
    if chat_history:
        st.markdown("### Conversation History")
        
        # Group messages into Q&A pairs (chat_history is already newest first from DB)
        qa_pairs = []
        i = 0
        while i < len(chat_history):
            # Messages come as: newest first (assistant answer, then user question)
            if chat_history[i]['role'] == 'assistant':
                assistant_msg = chat_history[i]
                
                # Look for corresponding user question
                user_msg = None
                if i + 1 < len(chat_history) and chat_history[i + 1]['role'] == 'user':
                    user_msg = chat_history[i + 1]
                    i += 2
                else:
                    i += 1
                
                if user_msg:
                    qa_pairs.append((assistant_msg, user_msg))
            else:
                i += 1
        
        # Reverse pairs so oldest appears first, newest at bottom
        qa_pairs.reverse()
        
        # Display Q&A pairs (oldest first, newest last)
        for assistant_msg, user_msg in qa_pairs:
            # Display user question first, then answer
            st.markdown(f"""
            <div class="chat-message user-message">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <strong>You</strong>
                    <span style="font-size: 0.8rem; opacity: 0.8;">{user_msg['timestamp'][:16]}</span>
                </div>
                <div>{user_msg['message']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="chat-message assistant-message">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <strong>Medical Assistant</strong>
                    <span style="font-size: 0.8rem; opacity: 0.8;">{assistant_msg['timestamp'][:16]}</span>
                </div>
                <div style="line-height: 1.7;">{assistant_msg['message']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="modern-card" style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
            <h4 style="color: #667eea; margin-bottom: 0.5rem;">Start a Conversation</h4>
            <p style="color: #666;">Ask me anything about your medical reports and health data</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input Section
    st.markdown("### Ask a Question")
    
    question = st.text_area(
        "Type your question here...",
        placeholder="E.g., What do my cholesterol levels indicate?",
        height=100,
        key="qa_question_input",
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns([1, 5])
    
    with col1:
        ask_button = st.button("Ask", type="primary", use_container_width=True)
    
    if ask_button and question:
        with st.spinner("Analyzing your question..."):
            # Save user question
            db.save_chat_message(
                user_id,
                report_id if report_id else 0,
                'user',
                question
            )
            
            # Get answer
            answer = qa_agent.answer_question(question, report_id)
            
            # Save assistant answer
            db.save_chat_message(
                user_id,
                report_id if report_id else 0,
                'assistant',
                answer
            )
            
            st.rerun()


def show_trends_page(user_id: str):
    """Modern trends page with interactive charts."""
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 2rem;">
        <h1>Health Trends</h1>
        <p>Track your health metrics over time</p>
    </div>
    """, unsafe_allow_html=True)
    
    reports = db.get_user_reports(user_id)
    
    if len(reports) < 2:
        st.markdown("""
        <div class="modern-card" style="text-align: center; padding: 3rem;">
            <h3 style="color: #667eea;">Need More Data</h3>
            <p style="color: #666; margin: 1rem 0;">Upload at least 2 reports to see health trends</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Collect all test data
    all_tests_data = {}
    
    for report in reports:
        report_details = db.get_report_details(report['id'])
        for test in report_details['test_results']:
            test_name = test['test_name']
            if test_name not in all_tests_data:
                all_tests_data[test_name] = []
            
            all_tests_data[test_name].append({
                'date': report['report_date'],
                'value': test['test_value'],
                'units': test['units'],
                'status': test['status']
            })
    
    trending_tests = {k: v for k, v in all_tests_data.items() if len(v) > 1}
    
    if not trending_tests:
        st.info("No tests found in multiple reports yet")
        return
    
    st.markdown(f"""
    <div class="modern-card">
        <h3 style="color: #667eea; margin-bottom: 0.5rem;">Tracking {len(trending_tests)} Tests</h3>
        <p style="color: #666;">Monitoring your health metrics across {len(reports)} reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabs for different views
    tabs = st.tabs(["All Trends", "Abnormal Trends", "Custom Analysis"])
    
    with tabs[0]:
        st.markdown("### All Test Trends")
        
        # Grid layout for trend cards
        test_names = list(trending_tests.keys())
        
        for i in range(0, len(test_names), 2):
            col1, col2 = st.columns(2)
            
            for idx, col in enumerate([col1, col2]):
                if i + idx < len(test_names):
                    test_name = test_names[i + idx]
                    data = trending_tests[test_name]
                    
                    with col:
                        with st.expander(f"{test_name}", expanded=False):
                            df = pd.DataFrame(data)
                            df['date'] = pd.to_datetime(df['date'])
                            df['numeric_value'] = pd.to_numeric(df['value'], errors='coerce')
                            
                            if not df['numeric_value'].isna().all():
                                fig = go.Figure()
                                
                                # Add line trace
                                fig.add_trace(go.Scatter(
                                    x=df['date'],
                                    y=df['numeric_value'],
                                    mode='lines+markers',
                                    name=test_name,
                                    line=dict(width=3, color='#667eea'),
                                    marker=dict(size=10, color='#764ba2')
                                ))
                                
                                fig.update_layout(
                                    title=f"{test_name} Over Time",
                                    xaxis_title="Date",
                                    yaxis_title=f"Value ({data[0]['units']})",
                                    hovermode='x unified',
                                    height=300,
                                    plot_bgcolor='white',
                                    paper_bgcolor='white',
                                    margin=dict(l=40, r=40, t=60, b=40)
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Show data table
                                st.dataframe(
                                    df[['date', 'value', 'units', 'status']],
                                    use_container_width=True,
                                    hide_index=True
                                )
    
    with tabs[1]:
        st.markdown("### Tests with Abnormal Results")
        
        abnormal_tests = {
            k: v for k, v in trending_tests.items()
            if any(d['status'] in ['high', 'low'] for d in v)
        }
        
        if not abnormal_tests:
            st.markdown("""
            <div class="modern-card" style="text-align: center; padding: 2rem; background: #d4edda;">
                <h4 style="color: #28a745;">All Tests Normal!</h4>
                <p style="color: #155724;">No abnormal trends detected in your recent reports</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for test_name, data in abnormal_tests.items():
                with st.expander(f"{test_name}", expanded=True):
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'])
                    df['numeric_value'] = pd.to_numeric(df['value'], errors='coerce')
                    
                    if not df['numeric_value'].isna().all():
                        fig = go.Figure()
                        
                        # Color-code by status
                        for status in df['status'].unique():
                            status_df = df[df['status'] == status]
                            color = '#dc3545' if status == 'high' else '#ffc107' if status == 'low' else '#28a745'
                            
                            fig.add_trace(go.Scatter(
                                x=status_df['date'],
                                y=status_df['numeric_value'],
                                mode='markers',
                                name=status.upper(),
                                marker=dict(size=12, color=color)
                            ))
                        
                        # Add connecting line
                        fig.add_trace(go.Scatter(
                            x=df['date'],
                            y=df['numeric_value'],
                            mode='lines',
                            name='Trend',
                            line=dict(width=2, color='#667eea', dash='dash'),
                            showlegend=False
                        ))
                        
                        fig.update_layout(
                            title=f"{test_name} - Abnormal Values Highlighted",
                            xaxis_title="Date",
                            yaxis_title=f"Value ({data[0]['units']})",
                            hovermode='x unified',
                            height=400,
                            plot_bgcolor='white'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Highlight abnormal readings
                        st.markdown("**Abnormal Readings:**")
                        abnormal_df = df[df['status'].isin(['high', 'low'])]
                        
                        for _, row in abnormal_df.iterrows():
                            status_color = "#dc3545" if row['status'] == 'high' else "#ffc107"
                            st.markdown(f"""
                            <div style="background: {status_color}22; padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid {status_color};">
                                <strong>{row['date'].strftime('%Y-%m-%d')}</strong>: {row['value']} {row['units']} 
                                <span style="color: {status_color}; font-weight: 600;">({row['status'].upper()})</span>
                            </div>
                            """, unsafe_allow_html=True)
    
    with tabs[2]:
        st.markdown("### Custom Trend Analysis")
        st.markdown("Compare multiple tests side by side")
        
        selected_tests = st.multiselect(
            "Select up to 3 tests to compare:",
            options=list(trending_tests.keys()),
            max_selections=3,
            key="custom_trends_select"
        )
        
        if selected_tests:
            fig = go.Figure()
            
            for test_name in selected_tests:
                data = trending_tests[test_name]
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df['numeric_value'] = pd.to_numeric(df['value'], errors='coerce')
                
                if not df['numeric_value'].isna().all():
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['numeric_value'],
                        mode='lines+markers',
                        name=test_name,
                        line=dict(width=3),
                        marker=dict(size=8)
                    ))
            
            fig.update_layout(
                title="Custom Test Comparison",
                xaxis_title="Date",
                yaxis_title="Value",
                hovermode='x unified',
                height=500,
                plot_bgcolor='white',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Statistics summary
            st.markdown("### Statistics Summary")
            
            cols = st.columns(len(selected_tests))
            
            for idx, test_name in enumerate(selected_tests):
                data = trending_tests[test_name]
                df = pd.DataFrame(data)
                df['numeric_value'] = pd.to_numeric(df['value'], errors='coerce')
                
                with cols[idx]:
                    st.markdown(f"""
                    <div class="modern-card">
                        <h4 style="color: #667eea; font-size: 1rem; margin-bottom: 1rem;">{test_name}</h4>
                        <div style="font-size: 0.85rem; color: #666;">
                            <strong>Latest:</strong> {data[-1]['value']} {data[-1]['units']}<br>
                            <strong>Min:</strong> {df['numeric_value'].min():.2f}<br>
                            <strong>Max:</strong> {df['numeric_value'].max():.2f}<br>
                            <strong>Avg:</strong> {df['numeric_value'].mean():.2f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


def show_history_page(user_id: str):
    """Modern history page with search and filters."""
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 2rem;">
        <h1>Report History</h1>
        <p>View and manage all your medical reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    reports = db.get_user_reports(user_id)
    
    if not reports:
        st.markdown("""
        <div class="modern-card" style="text-align: center; padding: 3rem;">
            <h3 style="color: #667eea;">No Reports Yet</h3>
            <p style="color: #666; margin: 1rem 0;">Upload your first medical report to get started</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Summary Stats
    st.markdown(f"""
    <div class="modern-card">
        <h3 style="color: #667eea; padding: 0.5rem 0 1rem;">Your Medical Archive</h3>
        <p style="color: #666; margin-bottom: 0.5rem;">You have <strong>{len(reports)}</strong> report(s) in your history</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Search and Filter
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        search = st.text_input("Search by filename:", "", key="history_search")
    
    with col2:
        sort_by = st.selectbox("Sort by:", ["Newest First", "Oldest First"], key="history_sort")
    
    with col3:
        view_mode = st.selectbox("View:", ["Grid", "List"], key="history_view")
    
    # Filter reports
    filtered_reports = reports
    if search:
        filtered_reports = [r for r in reports if search.lower() in r['filename'].lower()]
    
    if sort_by == "Oldest First":
        filtered_reports = list(reversed(filtered_reports))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Check if we should show report details
    if st.session_state.get('show_report_details') and st.session_state.get('current_report_id'):
        show_report_details_model(st.session_state.current_report_id, user_id)
        return  # Don't show the list when viewing details
    
    # Display reports
    if view_mode == "Grid":
        
        for i in range(0, len(filtered_reports), 2):
            col1, col2 = st.columns(2)
            
            for idx, col in enumerate([col1, col2]):
                if i + idx < len(filtered_reports):
                    report = filtered_reports[i + idx]
                    
                    with col:
                        st.markdown(f"""
                        <div class="report-card">
                            <div class="report-header">
                                <span class="report-icon">📄</span>
                                <h4 class="report-title">{report['filename'][:30]}{'...' if len(report['filename']) > 30 else ''}</h4>
                            </div>
                            <p class="report-date">Date: {report['report_date'][:10]}</p>
                            <div class="report-stats">
                                <div class="stat-item2">
                                    <div class="stat-label2">Total</div>
                                    <div class="stat-value2">{report['total_tests']}</div>
                                </div>
                                <div class="stat-item2">
                                    <div class="stat-label2">Normal</div>
                                    <div class="stat-value2">{report['normal_count']}</div>
                                </div>
                                <div class="stat-item2">
                                    <div class="stat-label2">Abnormal</div>
                                    <div class="stat-value2">{report['abnormal_count']}</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(
                            "VIEW DETAILS",
                            key=f"view_btn_{report['id']}",
                            use_container_width=False,
                            type="secondary"
                        ):
                            st.session_state.current_report_id = report['id']
                            st.session_state.show_report_details = True
                            st.rerun()
                        
                        st.markdown("<br>", unsafe_allow_html=True)
    
    else:
        # List view with expanders
        for report in filtered_reports:
            with st.expander(f"📄 {report['report_date'][:10]} - {report['filename']}", expanded=False):
                report_details = db.get_report_details(report['id'])
                
                # Report info
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Statistics**")
                    st.write(f"Total Tests: {report['total_tests']}")
                    st.write(f"Normal: {report['normal_count']}")
                    st.write(f"Abnormal: {report['abnormal_count']}")
                
                with col2:
                    st.markdown("**Patient Info**")
                    st.write(f"Age: {report['patient_age'] or 'N/A'}")
                    st.write(f"Gender: {report['patient_gender'] or 'Unknown'}")
                
                with col3:
                    st.markdown("**Actions**")
                    if st.button(
                        "View Full Report",
                        key=f"full_{report['id']}",
                        use_container_width=False
                    ):
                        st.session_state.current_report_id = report['id']
                        st.session_state.show_report_details = True
                        st.rerun()
                
                # Test results table
                if report_details['test_results']:
                    st.markdown("**Test Results:**")
                    
                    df_tests = pd.DataFrame(report_details['test_results'])
                    df_tests = df_tests[['test_name', 'test_value', 'units', 'status', 'reference_range']]
                    df_tests.columns = ['Test Name', 'Value', 'Units', 'Status', 'Normal Range']
                    
                    # Apply styling
                    def highlight_status(row):
                        if row['Status'] == 'high':
                            return ['background-color: #f8d7da'] * len(row)
                        elif row['Status'] == 'low':
                            return ['background-color: #fff3cd'] * len(row)
                        elif row['Status'] == 'normal':
                            return ['background-color: #d4edda'] * len(row)
                        else:
                            return [''] * len(row)
                    
                    st.dataframe(
                        df_tests.style.apply(highlight_status, axis=1),
                        use_container_width=True,
                        hide_index=True
                    )
                
                # Download PDF
                if report_details.get('pdf_path') and os.path.exists(report_details['pdf_path']):
                    with open(report_details['pdf_path'], 'rb') as f:
                        st.download_button(
                            label="Download PDF Report",
                            data=f,
                            file_name=f"report_{report['report_date'][:10]}.pdf",
                            mime="application/pdf",
                            key=f"download_{report['id']}",
                            use_container_width=False
                        )


def show_report_details_model(report_id: int, user_id: str):
    """Show detailed report in a full-page view."""
    
    # Back button at the top
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("Back to History", key="back_to_history", type="secondary"):
            st.session_state.show_report_details = False
            st.session_state.current_report_id = None
            st.rerun()
    
    st.markdown("---")
    # st.markdown("<br>", unsafe_allow_html=True)
    
    # Get report details
    report_details = db.get_report_details(report_id)
    
    # Header
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 2rem; padding: 1rem;">
        <h1 style="padding: 0;">Report Details</h1>
        <p style="margin-bottom: 0;">Comprehensive view of your medical report</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Report metadata
    st.markdown(f"### {report_details['filename']}")
    st.caption(f"Report Date: {report_details['report_date'][:10]}")
    
    # st.markdown("<br>", unsafe_allow_html=True)
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tests", report_details['total_tests'])
    with col2:
        st.metric("Normal", report_details['normal_count'])
    with col3:
        st.metric("Abnormal", report_details['abnormal_count'])
    with col4:
        st.metric("No Reference", report_details['no_reference_count'])
    
    st.markdown("---")
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Summary", "Test Results", "Ask Questions"])
    
    with tab1:
        # Summary
        if report_details.get('summary'):
            st.markdown("### Summary")
            import markdown
            summary_html = markdown.markdown(report_details['summary'], extensions=['extra', 'nl2br'])
            st.markdown(f"""
            <div class="summary-box-style">
                {summary_html}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Recommendations
        if report_details.get('recommendations'):
            st.markdown("### Key Recommendations")
            import markdown
            recommendations_html = markdown.markdown(report_details['recommendations'], extensions=['extra', 'nl2br'])
            st.markdown(f"""
            <div class="recommendation-box-style">
                {recommendations_html}
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        # Test Results
        st.markdown("### All Test Results")
        
        if report_details['test_results']:
            # Separate normal and abnormal tests
            abnormal_tests = [t for t in report_details['test_results'] if t['status'] in ['high', 'low']]
            normal_tests = [t for t in report_details['test_results'] if t['status'] == 'normal']
            other_tests = [t for t in report_details['test_results'] if t['status'] not in ['high', 'low', 'normal']]
            
            # Show abnormal tests first
            if abnormal_tests:
                st.markdown("#### Tests Requiring Attention")
                for test in abnormal_tests:
                    status_color = "red" if test['status'] == 'high' else "orange"
                    with st.expander(f"{test['test_name']} - {test['status'].upper()}", expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Value:** {test['test_value']} {test['units']}")
                            st.write(f"**Status:** {test['status'].upper()}")
                        with col2:
                            st.write(f"**Normal Range:** {test['reference_range']}")
                        
                        if test.get('analysis'):
                            st.info(test['analysis'])
                
                st.markdown("<br>", unsafe_allow_html=True)
            
            # Show normal tests
            if normal_tests:
                with st.expander(f"Normal Tests ({len(normal_tests)})", expanded=False):
                    df_normal = pd.DataFrame(normal_tests)
                    df_normal = df_normal[['test_name', 'test_value', 'units', 'reference_range']]
                    df_normal.columns = ['Test Name', 'Value', 'Units', 'Normal Range']
                    st.dataframe(df_normal, use_container_width=True, hide_index=True)
            
            # Show other tests
            if other_tests:
                with st.expander(f"Other Tests ({len(other_tests)})", expanded=False):
                    df_other = pd.DataFrame(other_tests)
                    df_other = df_other[['test_name', 'test_value', 'units']]
                    df_other.columns = ['Test Name', 'Value', 'Units']
                    st.dataframe(df_other, use_container_width=True, hide_index=True)
        else:
            st.info("No test results available")
    
    with tab3:
        # Quick link to Q&A
        st.markdown("### Ask Questions About This Report")
        st.info("You can ask specific questions about this report in the Q&A section")
        
        if st.button("Go to Q&A Section", type="primary", use_container_width=True):
            st.session_state.current_page = "Ask Questions"
            st.session_state.current_report_id = report_id
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Download button
    col1,col2,col3 = st.columns([1,2,1])
    with col2:
        if report_details.get('pdf_path') and os.path.exists(report_details['pdf_path']):
            with open(report_details['pdf_path'], 'rb') as f:
                st.download_button(
                    label="Download PDF",
                    data=f,
                    file_name=f"report_{report_details['report_date'][:10]}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )


def show_settings_page(user_id: str):
    """Modern settings page."""
    st.markdown("""
    <div class="hero-header" style="margin-bottom: 2rem;">
        <h1>Account Settings</h1>
        <p>Manage your profile and preferences</p>
    </div>
    """, unsafe_allow_html=True)
    
    user_profile = db.get_user_profile(user_id)
    
    tabs = st.tabs(["Profile", "Security", "Notifications", "About"])
    
    with tabs[0]:
        st.markdown("### Personal Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("Full Name", value=user_profile['full_name'], disabled=True, key="settings_name")
            st.text_input("Email", value=user_profile['email'], disabled=True, key="settings_email")
        
        with col2:
            if user_profile['date_of_birth']:
                st.text_input("Date of Birth", value=user_profile['date_of_birth'], disabled=True, key="settings_dob")
            if user_profile['gender']:
                st.text_input("Gender", value=user_profile['gender'], disabled=True, key="settings_gender")
        
        if user_profile['phone_number']:
            st.text_input("Phone Number", value=user_profile['phone_number'], disabled=True, key="settings_phone")
        
        st.markdown("---")
        st.markdown("### Account Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            status = "✅ Verified" if user_profile['is_verified'] else "❌ Not Verified"
            st.markdown(f"""
            <div class="metric-card {'success' if user_profile['is_verified'] else 'warning'}">
                <strong>Email Status:</strong><br>{status}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card info">
                <strong>Member Since:</strong><br>{user_profile['created_at'][:10]}
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[1]:
        st.markdown("### Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password", key="settings_curr_pass")
            new_password = st.text_input("New Password", type="password", key="settings_new_pass")
            confirm_password = st.text_input("Confirm New Password", type="password", key="settings_confirm_pass")
            
            if st.form_submit_button("Update Password", type="primary"):
                if not all([current_password, new_password, confirm_password]):
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    user_check = db.authenticate_user(user_profile['email'], current_password)
                    if not user_check:
                        st.error("Current password is incorrect")
                    else:
                        is_valid, msg = validate_password(new_password)
                        if not is_valid:
                            st.error(f"{msg}")
                        else:
                            if db.reset_password(user_profile['email'], new_password):
                                st.success("Password updated successfully!")
                                st.balloons()
                            else:
                                st.error("Failed to update password")
    
    with tabs[2]:
        st.markdown("### Email Notifications")
        
        st.checkbox("Report upload confirmations", value=True, key="notif_upload")
        st.checkbox("Weekly health summaries", value=False, key="notif_weekly")
        st.checkbox("Abnormal test alerts", value=True, key="notif_abnormal")
        st.checkbox("Account security alerts", value=True, key="notif_security")
        
        if st.button("Save Preferences", type="primary"):
            st.success("Notification preferences saved!")
    
    with tabs[3]:
        st.markdown("### About Medical Analysis Agent")
        
        st.markdown("""
        <div class="modern-card">
        <h4 style="color: #667eea;">Medical Analysis Agent</h4>
        <p style="color: #666; line-height: 1.8;">
            Medical Analysis Agent is an intelligent medical report analysis platform that helps you 
            understand your lab results with AI-powered insights. Our mission is to empower 
            individuals with clear, actionable health information.
        </p>
        
        <h4 style="color: #667eea; margin-top: 2rem;">Features</h4>
        <ul style="color: #666; line-height: 1.8;">
            <li>AI-powered medical report analysis</li>
            <li>Easy-to-understand health insights</li>
            <li>Trend tracking and visualization</li>
            <li>Personalized health recommendations</li>
            <li>Secure data storage and encryption</li>
        </ul>
        <h4 style="color: #667eea; margin-top: 2rem;">Contact &amp; Support</h4>
        <p style="color: #666;">
            <strong>Email:</strong> support@medicalanalysis.ai<br>
            <strong>Phone:</strong> 1-800-MEDICAL<br>
            <strong>Website:</strong> www.medicalanalysis.ai
        </p>
        
        <h4 style="color: #667eea; margin-top: 2rem;">Version Information</h4>
        <p style="color: #666;">
            <strong>Version:</strong> 1.0.0<br>
            <strong>Release Date:</strong> November 2024<br>
            <strong>License:</strong> Proprietary
        </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Privacy Policy", use_container_width=True):
                st.info("Privacy Policy page would open here")
        
        with col2:
            if st.button("Terms of Service", use_container_width=True):
                st.info("Terms of Service page would open here")


# ============== FOOTER ==============

def show_footer():
    """Professional footer with disclaimer."""
    st.markdown("---")
    
    # Medical Disclaimer Section
    st.markdown("""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #fff3cd 0%, #ffe5a0 100%); 
         border-radius: 12px; margin: 2rem 0; border-left: 4px solid rgb(246, 213, 116)'>
        <h3 style='color: #856404;'>Important Medical Disclaimer</h3>
        <p style='color: #856404; line-height: 1.8;'>
            <strong>Medical Analysis Agent</strong> is an informational tool designed to help you better understand your medical laboratory reports. 
            This platform uses artificial intelligence to analyze and interpret medical data, but it is <strong>NOT a substitute for professional medical advice</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Disclaimer Points
    st.markdown("""
    <div style='max-width: 900px; margin: 0 auto; text-align: left; padding: 0 2rem;'>
        <h4 style='color: #856404;'>Please Note:</h4>
        <ul style='color: #856404; line-height: 1.8;'>
            <li>This tool does not diagnose, treat, cure, or prevent any disease or medical condition</li>
            <li>All medical decisions should be made in consultation with qualified healthcare professionals</li>
            <li>Do not delay seeking medical advice based on information from this platform</li>
            <li>In case of medical emergency, call your local emergency services immediately</li>
            <li>Results and recommendations are for informational purposes only</li>
        </ul>
        <p style='color: #856404; line-height: 1.8; margin-top: 1rem;'>
            Always consult with your physician, healthcare provider, or qualified medical professional for proper interpretation 
            of your test results and for any questions regarding your health or medical conditions.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Branding Section
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0; border-top: 2px solid #e0e7ff;'>
        <h3 style='color: #667eea; margin: 0.5rem 0; font-size: 1.8rem; font-weight: 700;'>Medical Analysis Agent</h3>
        <p style='color: #666; font-size: 1.1rem; margin: 0.5rem 0;'>
            Empowering Health Understanding Through Artificial Intelligence
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Contact Grid
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style='text-align: center;'>
            <h4 style='color: #667eea; margin-bottom: 0.75rem;'>Contact Us</h4>
            <p style='color: #666; font-size: 0.9rem; line-height: 1.6;'>
                Email: support@medicalanalysis.ai<br>
                Phone: 1-800-MEDICAL<br>
                Hours: 24/7 Support
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='text-align: center;'>
            <h4 style='color: #667eea; margin-bottom: 0.75rem;'>Security</h4>
            <p style='color: #666; font-size: 0.9rem; line-height: 1.6;'>
                256-bit Encryption<br>
                HIPAA Compliant<br>
                SOC 2 Type II Certified
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style='text-align: center;'>
            <h4 style='color: #667eea; margin-bottom: 0.75rem;'>Connect</h4>
            <p style='color: #666; font-size: 0.9rem; line-height: 1.6;'>
                Twitter: @MedicalAI<br>
                LinkedIn: Medical Anlaysis Agent<br>
                Facebook: MedicalAnalysisOfficial
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style='text-align: center;'>
            <h4 style='color: #667eea; margin-bottom: 0.75rem;'>Resources</h4>
            <p style='color: #666; font-size: 0.9rem; line-height: 1.6;'>
                <a href="#" style="color: #667eea; text-decoration: none;">Help Center</a><br>
                <a href="#" style="color: #667eea; text-decoration: none;">API Docs</a><br>
                <a href="#" style="color: #667eea; text-decoration: none;">Blog</a>
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Copyright Section
    st.markdown("""
    <div style='margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e0e7ff; text-align: center;'>
        <p style='color: #999; font-size: 0.85rem; margin: 0.5rem 0;'>
            © 2024 Medical Analysis Technologies, Inc. All rights reserved.
        </p>
        <p style='color: #999; font-size: 0.85rem; margin: 0.5rem 0;'>
            <a href="#" style="color: #667eea; text-decoration: none; margin: 0 1rem;">Privacy Policy</a> | 
            <a href="#" style="color: #667eea; text-decoration: none; margin: 0 1rem;">Terms of Service</a> | 
            <a href="#" style="color: #667eea; text-decoration: none; margin: 0 1rem;">Cookie Policy</a> |
            <a href="#" style="color: #667eea; text-decoration: none; margin: 0 1rem;">Accessibility</a>
        </p>
        <p style='color: #999; font-size: 0.75rem; margin-top: 1rem;'>
            Medical Analysis Agent is a registered trademark. Patent pending technology.<br>
            Made with ❤️ for better health understanding worldwide.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ============== MAIN APPLICATION ENTRY POINT ==============

def main():
    """Main application entry point."""
    
    # Check authentication status
    if not st.session_state.logged_in:
        # Show authentication pages
        if st.session_state.auth_stage == 'login':
            show_login_page()
        elif st.session_state.auth_stage == 'signup':
            show_signup_page()
        elif st.session_state.auth_stage == 'verify_email':
            show_verify_email_page()
        elif st.session_state.auth_stage == 'forgot_password':
            show_forgot_password_page()
    else:
        # Show main application
        show_main_app()
    
    # Always show footer
    show_footer()


# Run the application
if __name__ == "__main__":
    main()
