import streamlit as st
from home import nav_bar

_SOCIALS_HTML = """
<div style="display:flex; gap:24px; justify-content:center; margin:8px 0 24px 0;">
  <a href="https://www.linkedin.com/in/leandrofabre" target="_blank"
     style="display:flex; align-items:center; gap:8px; text-decoration:none;
            background:#0A66C2; color:white; padding:10px 20px; border-radius:8px;
            font-weight:600; font-size:0.95rem;">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="white"
         xmlns="http://www.w3.org/2000/svg">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853
               0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9
               1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337
               7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063
               2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792
               0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2
               24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
    </svg>
    LinkedIn
  </a>
  <a href="https://github.com/Lelozitos" target="_blank"
     style="display:flex; align-items:center; gap:8px; text-decoration:none;
            background:#24292F; color:white; padding:10px 20px; border-radius:8px;
            font-weight:600; font-size:0.95rem;">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="white"
         xmlns="http://www.w3.org/2000/svg">
      <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111
               .793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387
               -1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084
               1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775
               .418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469
               -2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322
               3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404
               2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77
               .84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372
               .823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797
               24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
    </svg>
    GitHub
  </a>
  <a href="mailto:lm.fabre@hotmail.com"
     style="display:flex; align-items:center; gap:8px; text-decoration:none;
            background:#6C3DE8; color:white; padding:10px 20px; border-radius:8px;
            font-weight:600; font-size:0.95rem;">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="white"
         xmlns="http://www.w3.org/2000/svg">
      <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9
               2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
    </svg>
    Email
  </a>
</div>
"""

def main():
    nav_bar()

    st.title("📞 Contact")
    st.write("Questions, suggestions, or just want to talk F1 data? Reach out through any of the channels below.")

    st.markdown(_SOCIALS_HTML, unsafe_allow_html=True)
    st.divider()

    with st.form("contact_form"):
        st.subheader("Send a Message")
        c1, c2 = st.columns(2)
        name  = c1.text_input("Name")
        email = c2.text_input("Email")
        subject = st.selectbox("Subject", [
            "Bug report",
            "Feature request",
            "Data question",
            "General feedback",
            "Other",
        ])
        message = st.text_area("Message", height=140, placeholder="Write your message here…")

        submitted = st.form_submit_button("Send Message", icon="📩", use_container_width=True)
        if submitted:
            if not name or not email or not message:
                st.warning("Please fill in all fields before sending.")
            else:
                # Backend not yet implemented
                st.error("Message sending is not yet configured. Please reach out via LinkedIn or Email directly.")

main()
