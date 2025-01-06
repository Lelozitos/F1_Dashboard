import streamlit as st
from home import nav_bar
import requests

def main():
    nav_bar()

    st.title("Contact Me")
    
    cols = st.columns(6, gap="medium")
    cols[2].markdown("[![LinkedIn](https://raw.githubusercontent.com/danielcranney/readme-generator/main/public/icons/socials/linkedin.svg)](https://www.linkedin.com/in/leandrofabre)")
    cols[3].markdown("[![GitHub](https://raw.githubusercontent.com/danielcranney/readme-generator/main/public/icons/socials/github-dark.svg)](https://github.com/Lelozitos)")
    # cols[3].markdown("[![Email](public/icons/email.png)](mailto:lm.fabre@hotmail.com)")

    with st.form("Contact Me"):
        st.title("Send a Message")
        message = {
            "name": st.text_input("Name"),
            "email": st.text_input("Email"), # TODO validate email
            "message": st.text_area("Message")
        }


        if st.form_submit_button("Send", icon="📩"):
            st.error("Failed to send message.") # TODO send message

main()