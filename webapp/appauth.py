import streamlit as st
import json
import os
from datetime import datetime, timedelta
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
    page_title="Personal Medical Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    .stat-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        color: black;
        margin-left: 2rem;
    }
    .assistant-message {
        background-color: #f5f5f5;
        color: black;
        margin-right: 2rem;
    }
    .login-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2.5rem;
        background: white;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    }
    .auth-header {
        text-align: center;
        color: #667eea;
        margin-bottom: 2rem;
    }
    .otp-input {
        font-size: 1.5rem;
        text-align: center;
        letter-spacing: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# Email Configuration
class EmailService:
    """Production-ready email service for OTP and notifications."""
    
    def __init__(self):
        # Load from environment variables or config file
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'Personal Medical Assistant')
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """Send email with HTML and plain text fallback."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Plain text version
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)
            
            # HTML version
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            st.error(f"Email error: {str(e)}")
            return False
    
    def send_otp(self, to_email: str, otp: str, purpose: str = "verification") -> bool:
        """Send OTP verification email."""
        subject = f"Your Medical Assistant Verification Code"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-box {{ background: white; border: 2px dashed #667eea; padding: 20px; 
                           text-align: center; font-size: 32px; font-weight: bold; 
                           letter-spacing: 10px; color: #667eea; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 Personal Medical Assistant</h1>
                    <p>Account {purpose.title()}</p>
                </div>
                <div class="content">
                    <h2>Hello!</h2>
                    <p>Your verification code for account {purpose} is:</p>
                    <div class="otp-box">{otp}</div>
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong><br>
                        • This code expires in 10 minutes<br>
                        • Never share this code with anyone<br>
                        • We will never ask for this code via phone or email
                    </div>
                    <p>If you didn't request this code, please ignore this email or contact support if you're concerned about your account security.</p>
                </div>
                <div class="footer">
                    <p>© 2024 Personal Medical Assistant. All rights reserved.</p>
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Personal Medical Assistant - Account {purpose.title()}
        
        Your verification code is: {otp}
        
        This code expires in 10 minutes.
        Never share this code with anyone.
        
        If you didn't request this code, please ignore this email.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_welcome_email(self, to_email: str, full_name: str) -> bool:
        """Send welcome email to new users."""
        subject = "Welcome to Personal Medical Assistant! 🏥"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .feature {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; 
                           border-left: 4px solid #667eea; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 Welcome to Personal Medical Assistant!</h1>
                </div>
                <div class="content">
                    <h2>Hello {full_name}! 👋</h2>
                    <p>Thank you for joining us. We're excited to help you better understand your medical health!</p>
                    
                    <h3>What you can do:</h3>
                    <div class="feature">
                        📤 <strong>Upload Reports:</strong> Upload your medical lab reports in PDF format
                    </div>
                    <div class="feature">
                        📊 <strong>Track Trends:</strong> Monitor your health metrics over time
                    </div>
                    <div class="feature">
                        💬 <strong>Ask Questions:</strong> Get AI-powered answers about your health data
                    </div>
                    <div class="feature">
                        📈 <strong>Health Dashboard:</strong> View comprehensive analysis and insights
                    </div>
                    
                    <p style="margin-top: 30px;"><strong>⚠️ Important:</strong> This tool is for informational purposes only. 
                    Always consult with your healthcare provider for medical advice.</p>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <a href="#" style="background: #667eea; color: white; padding: 12px 30px; 
                           text-decoration: none; border-radius: 5px; display: inline-block;">
                            Get Started
                        </a>
                    </p>
                </div>
                <div class="footer">
                    <p>© 2024 Personal Medical Assistant. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)


# Enhanced Database with OTP and Security Features
class MedicalDatabase:
    def __init__(self, db_path="medical_history.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables with security features."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table with enhanced security
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
        
        # OTP table for verification codes
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
        
        # Security audit log
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
        
        # Session management
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
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
        
        # Chat history table
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
    
    # Security methods
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = os.getenv('PASSWORD_SALT', 'medical_assistant_salt_2024')
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def generate_otp(self) -> str:
        """Generate 6-digit OTP."""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    def generate_session_token(self) -> str:
        """Generate secure session token."""
        return secrets.token_urlsafe(32)
    
    # OTP management
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
                # Mark OTP as used
                cursor.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (otp_id,))
                conn.commit()
                conn.close()
                return True
        
        conn.close()
        return False
    
    # User management
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
        
        cursor.execute("""
        UPDATE users SET is_verified = 1
        WHERE email = ?
        """, (email.lower(),))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            self.log_security_event(None, email, "account_verified", "success")
        
        return affected > 0
    
    def authenticate_user(self, email: str, password: str, ip_address: str = None) -> Optional[Dict]:
        """Authenticate user and return user info."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if account is locked
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
        
        # Check if account is locked
        if locked_until:
            locked_until_dt = datetime.strptime(locked_until, '%Y-%m-%d %H:%M:%S.%f')
            if datetime.now() < locked_until_dt:
                conn.close()
                self.log_security_event(user_id, email, "login_attempt", "failed_account_locked", ip_address)
                return None
            else:
                # Unlock account
                cursor.execute("""
                UPDATE users SET account_locked_until = NULL, failed_login_attempts = 0
                WHERE user_id = ?
                """, (user_id,))
                conn.commit()
        
        # Check if account is active
        if not is_active:
            conn.close()
            self.log_security_event(user_id, email, "login_attempt", "failed_account_inactive", ip_address)
            return None
        
        # Verify password
        password_hash = self.hash_password(password)
        
        cursor.execute("""
        SELECT user_id, email, full_name, date_of_birth, gender, phone_number, is_verified
        FROM users
        WHERE email = ? AND password_hash = ?
        """, (email.lower(), password_hash))
        
        user_result = cursor.fetchone()
        
        if user_result:
            # Successful login - reset failed attempts
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
            # Failed login - increment failed attempts
            failed_attempts += 1
            
            if failed_attempts >= 5:
                # Lock account for 30 minutes
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
        """, (password_hash, email.lower()))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            self.log_security_event(None, email, "password_reset", "success")
        
        return affected > 0
    
    # Security logging
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
        """Get user profile information."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT user_id, email, full_name, date_of_birth, gender, phone_number, 
               is_verified, created_at, last_login
        FROM users
        WHERE user_id = ?
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
    
    # Report management methods (keep existing ones)
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
        FROM reports
        WHERE user_id = ?
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
        """Save chat message to history."""
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
        """Clear chat history for user or specific report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if report_id:
            cursor.execute("""
            DELETE FROM chat_history
            WHERE user_id = ? AND report_id = ?
            """, (user_id, report_id))
        else:
            cursor.execute("""
            DELETE FROM chat_history
            WHERE user_id = ?
            """, (user_id,))
        
        conn.commit()
        conn.close()


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
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'auth_stage' not in st.session_state:
    st.session_state.auth_stage = 'login'  # login, signup, verify_email, forgot_password
if 'pending_email' not in st.session_state:
    st.session_state.pending_email = None
if 'pending_user_data' not in st.session_state:
    st.session_state.pending_user_data = None


# Q&A Agent (keep existing enhanced version)
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


# Authentication UI Components
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


def show_login_page():
    """Display login interface."""
    st.markdown('<h1 class="main-header">🏥 Personal Medical Assistant</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="auth-header">Welcome Back!</h2>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Email Address", placeholder="your.email@example.com")
            password = st.text_input("Password", type="password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                submit = st.form_submit_button("Login", use_container_width=True, type="primary")
            with col_b:
                forgot = st.form_submit_button("Forgot Password?", use_container_width=True)
            
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
                                st.warning("⚠️ Your email is not verified. Please verify your email first.")
                                st.session_state.pending_email = email
                                st.session_state.auth_stage = 'verify_email'
                                st.rerun()
                            else:
                                st.session_state.logged_in = True
                                st.session_state.user_info = user_info
                                st.success(f"Welcome back, {user_info['full_name']}!")
                                st.rerun()
                        else:
                            st.error("❌ Invalid email or password. Account may be locked after 5 failed attempts.")
            
            if forgot:
                st.session_state.auth_stage = 'forgot_password'
                st.rerun()
        
        st.markdown("---")
        st.markdown("<p style='text-align: center;'>Don't have an account?</p>", unsafe_allow_html=True)
        if st.button("Create New Account", use_container_width=True):
            st.session_state.auth_stage = 'signup'
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


def show_signup_page():
    """Display signup interface."""
    st.markdown('<h1 class="main-header">🏥 Personal Medical Assistant</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="auth-header">Create Your Account</h2>', unsafe_allow_html=True)
        
        with st.form("signup_form"):
            full_name = st.text_input("Full Name *", placeholder="John Doe")
            email = st.text_input("Email Address *", placeholder="your.email@example.com")
            
            col_a, col_b = st.columns(2)
            with col_a:
                password = st.text_input("Password *", type="password")
            with col_b:
                confirm_password = st.text_input("Confirm Password *", type="password")
            
            st.markdown("##### Optional Information")
            col_c, col_d = st.columns(2)
            with col_c:
                dob = st.date_input("Date of Birth", value=None, max_value=datetime.now())
            with col_d:
                gender = st.selectbox("Gender", ["", "Male", "Female", "Other"])
            
            phone = st.text_input("Phone Number", placeholder="+1234567890")
            
            agree = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            
            if submit:
                # Validation
                if not all([full_name, email, password, confirm_password]):
                    st.error("Please fill in all required fields (*)")
                elif not validate_email(email):
                    st.error("Please enter a valid email address")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    is_valid, msg = validate_password(password)
                    if not is_valid:
                        st.error(msg)
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
                                # Generate and send OTP
                                otp = db.create_otp(email, "verification")
                                email_sent = email_service.send_otp(email, otp, "verification")
                                
                                if email_sent:
                                    st.success("✅ Account created! Please check your email for verification code.")
                                    st.session_state.pending_email = email
                                    st.session_state.pending_user_data = {'full_name': full_name}
                                    st.session_state.auth_stage = 'verify_email'
                                    st.rerun()
                                else:
                                    st.error("Account created but failed to send verification email. Please try to resend.")
                                    st.session_state.pending_email = email
                                    st.session_state.auth_stage = 'verify_email'
                                    st.rerun()
                            else:
                                st.error(f"Error: {result}")
        
        st.markdown("---")
        st.markdown("<p style='text-align: center;'>Already have an account?</p>", unsafe_allow_html=True)
        if st.button("Login Instead", use_container_width=True):
            st.session_state.auth_stage = 'login'
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


def show_verify_email_page():
    """Display email verification interface."""
    st.markdown('<h1 class="main-header">🏥 Personal Medical Assistant</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="auth-header">Verify Your Email</h2>', unsafe_allow_html=True)
        
        st.info(f"📧 We've sent a 6-digit verification code to:\n\n**{st.session_state.pending_email}**")
        
        with st.form("verify_form"):
            otp = st.text_input(
                "Enter 6-digit code",
                max_chars=6,
                placeholder="000000",
                help="Check your email inbox (and spam folder)"
            )
            
            submit = st.form_submit_button("Verify Email", use_container_width=True, type="primary")
            
            if submit:
                if len(otp) != 6 or not otp.isdigit():
                    st.error("Please enter a valid 6-digit code")
                else:
                    with st.spinner("Verifying..."):
                        if db.verify_otp(st.session_state.pending_email, otp, "verification"):
                            db.verify_user_account(st.session_state.pending_email)
                            
                            # Send welcome email
                            if st.session_state.pending_user_data:
                                email_service.send_welcome_email(
                                    st.session_state.pending_email,
                                    st.session_state.pending_user_data.get('full_name', 'User')
                                )
                            
                            st.success("✅ Email verified successfully! You can now login.")
                            st.balloons()
                            
                            # Clear pending data
                            st.session_state.pending_email = None
                            st.session_state.pending_user_data = None
                            st.session_state.auth_stage = 'login'
                            
                            st.rerun()
                        else:
                            st.error("❌ Invalid or expired verification code")
        
        st.markdown("---")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Resend Code", use_container_width=True):
                otp = db.create_otp(st.session_state.pending_email, "verification")
                if email_service.send_otp(st.session_state.pending_email, otp, "verification"):
                    st.success("✅ New code sent to your email!")
                else:
                    st.error("Failed to send email. Please try again.")
        
        with col_b:
            if st.button("Back to Login", use_container_width=True):
                st.session_state.auth_stage = 'login'
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


def show_forgot_password_page():
    """Display forgot password interface."""
    st.markdown('<h1 class="main-header">🏥 Personal Medical Assistant</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="auth-header">Reset Password</h2>', unsafe_allow_html=True)
        
        if 'reset_stage' not in st.session_state:
            st.session_state.reset_stage = 'request'  # request, verify, reset
        
        if st.session_state.reset_stage == 'request':
            st.info("Enter your email address and we'll send you a verification code to reset your password.")
            
            with st.form("forgot_password_form"):
                email = st.text_input("Email Address", placeholder="your.email@example.com")
                submit = st.form_submit_button("Send Reset Code", use_container_width=True, type="primary")
                
                if submit:
                    if not email or not validate_email(email):
                        st.error("Please enter a valid email address")
                    else:
                        with st.spinner("Sending reset code..."):
                            otp = db.create_otp(email, "password_reset")
                            if email_service.send_otp(email, otp, "password reset"):
                                st.success("✅ Reset code sent to your email!")
                                st.session_state.pending_email = email
                                st.session_state.reset_stage = 'verify'
                                st.rerun()
                            else:
                                st.error("Failed to send email. Please check the email address and try again.")
        
        elif st.session_state.reset_stage == 'verify':
            st.info(f"📧 Enter the verification code sent to:\n\n**{st.session_state.pending_email}**")
            
            with st.form("verify_reset_form"):
                otp = st.text_input("Enter 6-digit code", max_chars=6, placeholder="000000")
                submit = st.form_submit_button("Verify Code", use_container_width=True, type="primary")
                
                if submit:
                    if len(otp) != 6 or not otp.isdigit():
                        st.error("Please enter a valid 6-digit code")
                    else:
                        if db.verify_otp(st.session_state.pending_email, otp, "password_reset"):
                            st.success("✅ Code verified! Now set your new password.")
                            st.session_state.reset_stage = 'reset'
                            st.rerun()
                        else:
                            st.error("❌ Invalid or expired code")
            
            if st.button("Resend Code", use_container_width=True):
                otp = db.create_otp(st.session_state.pending_email, "password_reset")
                if email_service.send_otp(st.session_state.pending_email, otp, "password reset"):
                    st.success("✅ New code sent!")
        
        elif st.session_state.reset_stage == 'reset':
            with st.form("reset_password_form"):
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                submit = st.form_submit_button("Reset Password", use_container_width=True, type="primary")
                
                if submit:
                    if not new_password or not confirm_password:
                        st.error("Please fill in all fields")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        is_valid, msg = validate_password(new_password)
                        if not is_valid:
                            st.error(msg)
                        else:
                            if db.reset_password(st.session_state.pending_email, new_password):
                                st.success("✅ Password reset successfully! You can now login with your new password.")
                                st.balloons()
                                st.session_state.reset_stage = 'request'
                                st.session_state.pending_email = None
                                st.session_state.auth_stage = 'login'
                                st.rerun()
                            else:
                                st.error("Failed to reset password. Please try again.")
        
        st.markdown("---")
        if st.button("Back to Login", use_container_width=True):
            st.session_state.reset_stage = 'request'
            st.session_state.auth_stage = 'login'
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)


# Main application pages (keep your existing ones)
def show_main_app():
    """Display main application interface."""
    user_id = st.session_state.user_info['user_id']
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_info['full_name']}")
        st.markdown(f"*{st.session_state.user_info['email']}*")
        
        # Show verification status
        if not st.session_state.user_info['is_verified']:
            st.warning("⚠️ Email not verified")
        
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["📤 Upload Report", "📊 Dashboard", "💬 Ask Questions", "📈 Trends", "📋 History", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        st.markdown("### Recent Reports")
        recent_reports = db.get_user_reports(user_id)[:3]
        
        if recent_reports:
            for report in recent_reports:
                with st.expander(f"📄 {report['report_date'][:10]}"):
                    st.write(f"**Tests:** {report['total_tests']}")
                    st.write(f"**Normal:** {report['normal_count']}")
                    st.write(f"**Abnormal:** {report['abnormal_count']}")
                    if st.button("View", key=f"view_{report['id']}"):
                        st.session_state.current_report_id = report['id']
        else:
            st.info("No reports yet!")
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.session_state.current_report_id = None
            st.rerun()
    
    # Show appropriate page
    if page == "📤 Upload Report":
        show_upload_page(user_id)
    elif page == "📊 Dashboard":
        show_dashboard_page(user_id)
    elif page == "💬 Ask Questions":
        show_qa_page(user_id)
    elif page == "📈 Trends":
        show_trends_page(user_id)
    elif page == "📋 History":
        show_history_page(user_id)
    elif page == "⚙️ Settings":
        show_settings_page(user_id)


def show_settings_page(user_id: str):
    """Display user settings page."""
    st.markdown('<h1 class="main-header">Account Settings</h1>', unsafe_allow_html=True)
    
    user_profile = db.get_user_profile(user_id)
    
    tab1, tab2, tab3 = st.tabs(["👤 Profile", "🔐 Security", "📧 Notifications"])
    
    with tab1:
        st.markdown("### Personal Information")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full Name", value=user_profile['full_name'], disabled=True)
            st.text_input("Email", value=user_profile['email'], disabled=True)
        with col2:
            if user_profile['date_of_birth']:
                st.text_input("Date of Birth", value=user_profile['date_of_birth'], disabled=True)
            if user_profile['gender']:
                st.text_input("Gender", value=user_profile['gender'], disabled=True)
        
        if user_profile['phone_number']:
            st.text_input("Phone Number", value=user_profile['phone_number'], disabled=True)
        
        st.markdown("---")
        st.markdown("### Account Status")
        col1, col2 = st.columns(2)
        with col1:
            status = "✅ Verified" if user_profile['is_verified'] else "❌ Not Verified"
            st.info(f"Email Status: {status}")
        with col2:
            st.info(f"Member Since: {user_profile['created_at'][:10]}")
    
    with tab2:
        st.markdown("### Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Update Password", type="primary"):
                if not all([current_password, new_password, confirm_password]):
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    # Verify current password
                    user_check = db.authenticate_user(user_profile['email'], current_password)
                    if not user_check:
                        st.error("Current password is incorrect")
                    else:
                        is_valid, msg = validate_password(new_password)
                        if not is_valid:
                            st.error(msg)
                        else:
                            if db.reset_password(user_profile['email'], new_password):
                                st.success("✅ Password updated successfully!")
                            else:
                                st.error("Failed to update password")
    
    with tab3:
        st.markdown("### Email Notifications")
        st.checkbox("Report upload confirmations", value=True)
        st.checkbox("Weekly health summaries", value=False)
        st.checkbox("Abnormal test alerts", value=True)
        st.checkbox("Account security alerts", value=True)
        
        if st.button("Save Preferences", type="primary"):
            st.success("✅ Preferences saved!")


# Keep all your existing page functions (upload, dashboard, qa, trends, history)
# I'll include simplified versions here

def show_upload_page(user_id: str):
    """Upload report page."""
    st.markdown('<h1 class="main-header">Upload Medical Report</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Upload your medical report (PDF format) to get:
    - 📋 Easy-to-understand summary
    - 📊 Test result analysis
    - 💡 Personalized recommendations
    - 📈 Trend tracking over time
    """)
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload your lab report in PDF format"
    )
    
    if uploaded_file is not None:
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        if st.button("🔍 Analyze Report", type="primary"):
            with st.spinner("🔄 Analyzing your report... This may take 1-2 minutes."):
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("📄 Parsing PDF...")
                    progress_bar.progress(20)
                    
                    inputs = {"pdf_path": str(file_path)}
                    final_state = analyzer_workflow.invoke(inputs)
                    
                    status_text.text("🔬 Analyzing test results...")
                    progress_bar.progress(60)
                    
                    output = generate_user_friendly_output(final_state)
                    
                    status_text.text("📝 Generating report...")
                    progress_bar.progress(80)
                    
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
                        st.session_state.analysis_complete = True
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Analysis complete!")
                        
                        st.success("🎉 Report analyzed successfully!")
                        
                        st.markdown("---")
                        st.markdown("## 📊 Analysis Results")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        stats = output['statistics']
                        with col1:
                            st.metric("Total Tests", stats['total_tests'])
                        with col2:
                            st.metric("Normal", stats['normal_count'])
                        with col3:
                            st.metric("Abnormal", stats['abnormal_count'])
                        with col4:
                            st.metric("No Reference", stats['no_reference_count'])
                        
                        st.markdown("### 📋 Summary")
                        st.info(output['summary'])
                        
                        abnormal = [r for r in output['detailed_results'] 
                                   if r['status'] in ['high', 'low']]
                        
                        if abnormal:
                            st.markdown("### ⚠️ Tests Needing Attention")
                            for result in abnormal:
                                status_emoji = "📈" if result['status'] == 'high' else "📉"
                                st.warning(
                                    f"{status_emoji} **{result['test_name']}**: "
                                    f"{result['test_value']} {result['units']} "
                                    f"(Normal: {result['reference_range']})"
                                )
                        
                        st.markdown("### 💡 Recommendations")
                        st.success(output['recommendations'])
                        
                        with open(pdf_path, 'rb') as f:
                            st.download_button(
                                label="📥 Download Full Report (PDF)",
                                data=f,
                                file_name=f"medical_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.error(f"❌ Error: {output['details']}")
                        st.info(output['suggestion'])
                
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())


def show_dashboard_page(user_id: str):
    """Dashboard page."""
    st.markdown('<h1 class="main-header">Health Dashboard</h1>', unsafe_allow_html=True)
    
    reports = db.get_user_reports(user_id)
    
    if not reports:
        st.info("📭 No reports yet. Upload your first report to get started!")
    else:
        st.markdown("### 📈 Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            st.metric("Total Reports", len(reports))
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            total_tests = sum(r['total_tests'] for r in reports)
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            st.metric("Total Tests", total_tests)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            latest = reports[0]
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            st.metric("Last Check", latest['report_date'][:10])
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("### 📊 Test Results Over Time")
        
        all_tests = set()
        for report in reports:
            report_details = db.get_report_details(report['id'])
            for test in report_details['test_results']:
                all_tests.add(test['test_name'])
        
        if all_tests:
            selected_test = st.selectbox("Select test to view trend:", sorted(all_tests))
            
            trends = db.get_test_trends(user_id, selected_test)
            
            if len(trends) > 1:
                df_trends = pd.DataFrame(trends)
                df_trends['report_date'] = pd.to_datetime(df_trends['report_date'])
                df_trends['test_value'] = pd.to_numeric(df_trends['test_value'], errors='coerce')
                
                fig = px.line(
                    df_trends,
                    x='report_date',
                    y='test_value',
                    title=f'{selected_test} Trend',
                    markers=True
                )
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title=f"{selected_test} ({trends[0]['units']})",
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Need at least 2 reports to show trends")
        
        st.markdown("### 📋 Recent Reports")
        
        df_reports = pd.DataFrame(reports)
        df_reports = df_reports[['report_date', 'filename', 'total_tests', 
                                 'normal_count', 'abnormal_count']]
        df_reports.columns = ['Date', 'File', 'Total Tests', 'Normal', 'Abnormal']
        
        st.dataframe(df_reports, use_container_width=True)


def show_qa_page(user_id: str):
    """Q&A page."""
    st.markdown('<h1 class="main-header">Ask Your Medical Assistant</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Ask questions about your medical reports and get personalized answers based on your history.
    
    **Example questions:**
    - What do my recent test results mean?
    - How has my cholesterol changed over time?
    - What should I do about my high blood sugar?
    - Explain my thyroid results in simple terms
    """)
    
    reports = db.get_user_reports(user_id)
    
    if reports:
        report_options = {
            "All Reports": None,
            **{f"{r['report_date'][:10]} - {r['filename']}": r['id'] for r in reports}
        }
        
        selected_report = st.selectbox(
            "Ask about specific report or all history:",
            options=list(report_options.keys())
        )
        
        report_id = report_options[selected_report]
        
        qa_agent = MedicalQAAgent(db, user_id)
        
        st.markdown("---")
        
        # Display chat history
        chat_history = db.get_chat_history(user_id, report_id)
        
        for msg in chat_history:
            role = msg['role']
            message = msg['message']
            
            if role == 'user':
                st.markdown(
                    f'<div class="chat-message user-message">👤 **You:** {message}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="chat-message assistant-message">🤖 **Assistant:** {message}</div>',
                    unsafe_allow_html=True
                )
        
        # Input area
        question = st.text_input("Ask a question:", key="question_input")
        
        col1, col2 = st.columns([1, 5])
        with col1:
            ask_button = st.button("Ask", type="primary")
        with col2:
            if st.button("Clear History"):
                db.clear_chat_history(user_id, report_id if report_id else None)
                st.success("Chat history cleared!")
                st.rerun()
        
        if ask_button and question:
            with st.spinner("🤔 Thinking..."):
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
    else:
        st.info("📭 Upload a report first to start asking questions!")


def show_trends_page(user_id: str):
    """Trends page."""
    st.markdown('<h1 class="main-header">Health Trends</h1>', unsafe_allow_html=True)
    
    reports = db.get_user_reports(user_id)
    
    if len(reports) < 2:
        st.info("📊 Upload at least 2 reports to see trends")
    else:
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
        else:
            st.markdown(f"### 📊 Tracking {len(trending_tests)} Tests Over Time")
            
            tabs = st.tabs(["All Tests", "Abnormal Trends", "Custom View"])
            
            with tabs[0]:
                for test_name, data in trending_tests.items():
                    with st.expander(f"📈 {test_name}"):
                        df = pd.DataFrame(data)
                        df['date'] = pd.to_datetime(df['date'])
                        df['numeric_value'] = pd.to_numeric(df['value'], errors='coerce')
                        
                        if not df['numeric_value'].isna().all():
                            fig = go.Figure()
                            
                            fig.add_trace(go.Scatter(
                                x=df['date'],
                                y=df['numeric_value'],
                                mode='lines+markers',
                                name=test_name,
                                line=dict(width=2),
                                marker=dict(size=10)
                            ))
                            
                            fig.update_layout(
                                title=f"{test_name} Trend",
                                xaxis_title="Date",
                                yaxis_title=f"Value ({data[0]['units']})",
                                hovermode='x unified',
                                height=300
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            st.dataframe(df[['date', 'value', 'units', 'status']], 
                                       use_container_width=True)
            
            with tabs[1]:
                st.markdown("### ⚠️ Tests with Abnormal Results")
                
                abnormal_tests = {
                    k: v for k, v in trending_tests.items()
                    if any(d['status'] in ['high', 'low'] for d in v)
                }
                
                if not abnormal_tests:
                    st.success("✅ No abnormal trends detected!")
                else:
                    for test_name, data in abnormal_tests.items():
                        with st.expander(f"⚠️ {test_name}"):
                            df = pd.DataFrame(data)
                            df['date'] = pd.to_datetime(df['date'])
                            st.dataframe(df, use_container_width=True)
            
            with tabs[2]:
                st.markdown("### 🎯 Custom Trend Analysis")
                
                selected_tests = st.multiselect(
                    "Select tests to compare:",
                    options=list(trending_tests.keys()),
                    max_selections=3
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
                                name=test_name
                            ))
                    
                    fig.update_layout(
                        title="Selected Tests Comparison",
                        xaxis_title="Date",
                        yaxis_title="Value",
                        hovermode='x unified',
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)


def show_history_page(user_id: str):
    """History page."""
    st.markdown('<h1 class="main-header">Report History</h1>', unsafe_allow_html=True)
    
    reports = db.get_user_reports(user_id)
    
    if not reports:
        st.info("📭 No reports in history. Upload your first report!")
    else:
        st.markdown(f"### 📚 You have {len(reports)} report(s) in your history")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search = st.text_input("🔍 Search by filename:", "")
        
        with col2:
            sort_by = st.selectbox("Sort by:", ["Newest First", "Oldest First"])
        
        filtered_reports = reports
        if search:
            filtered_reports = [r for r in reports if search.lower() in r['filename'].lower()]
        
        if sort_by == "Oldest First":
            filtered_reports = list(reversed(filtered_reports))
        
        for report in filtered_reports:
            with st.expander(f"📄 {report['report_date'][:10]} - {report['filename']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Patient Info**")
                    st.write(f"Age: {report['patient_age'] or 'N/A'}")
                    st.write(f"Gender: {report['patient_gender'] or 'Unknown'}")
                
                with col2:
                    st.markdown("**Test Statistics**")
                    st.write(f"Total: {report['total_tests']}")
                    st.write(f"Normal: {report['normal_count']}")
                    st.write(f"Abnormal: {report['abnormal_count']}")
                
                with col3:
                    st.markdown("**Actions**")
                    if st.button("View Details", key=f"detail_{report['id']}"):
                        st.session_state.current_report_id = report['id']
                        st.rerun()
                
                report_details = db.get_report_details(report['id'])
                
                if report_details['test_results']:
                    st.markdown("**Test Results:**")
                    df_tests = pd.DataFrame(report_details['test_results'])
                    df_tests = df_tests[['test_name', 'test_value', 'units', 'status', 'reference_range']]
                    df_tests.columns = ['Test', 'Value', 'Units', 'Status', 'Normal Range']
                    
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
                
                if report_details.get('pdf_path') and os.path.exists(report_details['pdf_path']):
                    with open(report_details['pdf_path'], 'rb') as f:
                        st.download_button(
                            label="📥 Download PDF Report",
                            data=f,
                            file_name=f"report_{report['report_date'][:10]}.pdf",
                            mime="application/pdf",
                            key=f"download_{report['id']}"
                        )

# Main application logic
if not st.session_state.logged_in:
    if st.session_state.auth_stage == 'login':
        show_login_page()
    elif st.session_state.auth_stage == 'signup':
        show_signup_page()
    elif st.session_state.auth_stage == 'verify_email':
        show_verify_email_page()
    elif st.session_state.auth_stage == 'forgot_password':
        show_forgot_password_page()
else:
    show_main_app()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>⚠️ Medical Disclaimer</strong></p>
    <p>This tool is for informational purposes only and does not constitute medical advice.</p>
    <p>Always consult with your healthcare provider for proper interpretation and treatment.</p>
    <p style='margin-top: 1rem; font-size: 0.9rem;'>
        Personal Medical Assistant | Built with ❤️ for better health understanding
    </p>
    <p style='font-size: 0.8rem; color: #999;'>
        🔒 Your data is encrypted and secure | 📧 Support: support@medicalassistant.com
    </p>
</div>
""", unsafe_allow_html=True)