def verification_email_html(verify_url):
    return f"""
    <div style='background:#0b1220; padding:20px; color:white; font-family:Arial;'>
        <h2 style='color:#93c5fd;'>Verify Your Email</h2>
        <p>Please click the button below to verify your Leaders.st account:</p>
        <a href='{verify_url}' style='padding:10px 18px; background:#2563eb; color:white; text-decoration:none; border-radius:6px;'>Verify Email</a>
        <p>If you didn’t request this, ignore this email.</p>
    </div>
    """


def reset_password_email_html(reset_url):
    return f"""
    <div style='background:#0b1220; padding:20px; color:white; font-family:Arial;'>
        <h2 style='color:#93c5fd;'>Reset Your Password</h2>
        <p>Click the button below to reset your password:</p>
        <a href='{reset_url}' style='padding:10px 18px; background:#2563eb; color:white; text-decoration:none; border-radius:6px;'>Reset Password</a>
        <p>This link expires in 1 hour.</p>
    </div>
    """
