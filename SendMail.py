import smtplib, ssl

SMTP_SSL_PORT = 465
EMAIL_ADDRESS = "patrickjmccauley.dev@gmail.com"

def send_mail(subject, message, to_address=EMAIL_ADDRESS):
    """ Simple wrapper to send email. Intent is to be used on script failure
    """
    # Init values, consume credential
    port = SMTP_SSL_PORT
    f = open("cred.pickle")
    password = f.read()
    f.close()

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Send the mail
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(EMAIL_ADDRESS, password)
        msg = "Subject: {}\n\n{}".format(subject, message)
        server.sendmail(EMAIL_ADDRESS, to_address, msg)


def main():
    # Testing the code
    send_mail("Testing email send", "Testing")


if __name__ == "__main__":
    main()