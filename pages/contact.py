import streamlit as st
from home import nav_bar
import requests

def main():
    nav_bar()

    st.title("Contact Me")
    st.write("")
    cols = st.columns(6, gap="medium")
    cols[2].markdown("[![LinkedIn](https://raw.githubusercontent.com/danielcranney/readme-generator/main/public/icons/socials/linkedin.svg)](https://www.linkedin.com/in/leandrofabre)")
    cols[3].markdown("[![GitHub](https://raw.githubusercontent.com/danielcranney/readme-generator/main/public/icons/socials/github-dark.svg)](https://github.com/Lelozitos)")
    # cols[3].markdown("[![Email](public/icons/email.png)](mailto:lm.fabre@hotmail.com)")

    st.title("Send a Message")
    message = {
        "name": st.text_input("Name"),
        "email": st.text_input("Email"), # TODO validate email
        "message": st.text_area("Message")
    }

    _, cols = st.columns([10, 1])
    if cols.button("Send"):
        response = requests.post("https://formsubmit.co/lm.fabre@hotmail.com", json=message) # TODO not working

        # if response.status_code == 200:
        #     st.success("Message sent successfully")
        # else:
        st.error("Message not sent")

main()