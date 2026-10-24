package service

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/smtp"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/sadguruchenu/thoughtsgo/internal/config"
)

const (
	brandName    = "Memo"
	brandColor   = "#18181b"
	githubURL    = "https://github.com/sadhguru-slayer"
	footerCredit = `Built with ♥ by <a href="` + githubURL + `" class="footer-link" style="color:#18181b;text-decoration:none;font-weight:600;" target="_blank">Sadguru</a>`
)

const emailStyle = `
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%}
  .wrap{width:100%;background:#f4f4f5;padding:48px 16px}
  .card{max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #e4e4e7;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px 0 rgba(0,0,0,0.05),0 1px 2px 0 rgba(0,0,0,0.06)}
  .body{padding:40px 32px 32px 32px}
  .subtitle{font-size:14px;color:#71717a;line-height:1.5;margin-bottom:24px}
  .otp-wrap{margin:0 0 24px}
  .otp-label{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#a1a1aa;margin-bottom:8px}
  .otp-box{display:inline-block;padding:16px 24px;font-size:32px;font-weight:700;letter-spacing:8px;font-family:SFMono-Regular,Consolas,"Liberation Mono",Menlo,monospace;background:#fafafa;border:1px solid #e4e4e7;border-radius:10px;color:#09090b}
  .note{font-size:13px;color:#52525b;line-height:1.5;background:#f4f4f5;border-radius:8px;padding:12px 16px}
  
  .content-box{background:#fafafa;border:1px solid #e4e4e7;border-left:3px solid #09090b;border-radius:8px;padding:20px;margin-bottom:20px;text-align:left}
  .task-title{font-size:16px;font-weight:700;color:#09090b;text-decoration:none;line-height:1.35;display:block;word-break:break-word}
  .task-desc{margin:10px 0 0;font-size:14px;color:#52525b;line-height:1.6}
  .cta-btn-wrap{margin-top:18px}
  .cta-btn{display:inline-block;padding:10px 20px;background:#09090b;color:#ffffff;font-size:13px;font-weight:600;border-radius:8px;text-decoration:none;letter-spacing:.2px;transition:background-color 0.15s ease}
  .cta-btn-center{display:inline-block;padding:12px 24px;background:#09090b;color:#ffffff;font-size:13px;font-weight:600;border-radius:8px;text-decoration:none;letter-spacing:.2px;transition:background-color 0.15s ease}
  
  .divider{border:none;border-top:1px solid #e4e4e7;margin:28px 0}
  .footer{padding:0;text-align:center}
  .footer p{font-size:12px;color:#71717a;line-height:1.6}
  .footer a{color:#09090b;text-decoration:none;font-weight:600}
  .badge{display:inline-block;margin-top:12px;font-size:11px;color:#a1a1aa;letter-spacing:.3px}

  @media only screen and (max-width:480px){
    .wrap{padding:24px 10px}
    .body{padding:28px 20px 24px 20px}
    .otp-box{font-size:26px;letter-spacing:6px;padding:14px 20px}
    .header-title{font-size:18px!important}
  }
  @media (prefers-color-scheme:dark){
    body,.wrap{background:#09090b!important}
    .card{background:#09090b!important;border-color:#27272a!important;box-shadow:none!important}
    .header-title{color:#f4f4f5!important}
    .header-pre{color:#a1a1aa!important}
    .subtitle{color:#a1a1aa!important}
    .otp-box{background:#18181b!important;border-color:#27272a!important;color:#f4f4f5!important}
    .note{background:#18181b!important;border-color:#27272a!important;color:#a1a1aa!important}
    .content-box{background:#18181b!important;border-color:#27272a!important;border-left-color:#f4f4f5!important;color:#f4f4f5!important}
    .task-title{color:#f4f4f5!important}
    .task-desc{color:#a1a1aa!important}
    .cta-btn,.cta-btn-center{background:#f4f4f5!important;color:#09090b!important}
    .divider{border-color:#27272a!important}
    .footer p{color:#71717a!important}
    .footer a{color:#f4f4f5!important}
    .badge{color:#71717a!important}
  }
`

type EmailService struct {
	cfg *config.Config
}

func NewEmailService(cfg *config.Config) *EmailService {
	return &EmailService{cfg: cfg}
}

func (s *EmailService) htmlHeader(icon, title, subtitle, category string) string {
	subRow := ""
	if subtitle != "" {
		subRow = fmt.Sprintf(`<p class="subtitle" style="font-size:14px;color:#71717a;line-height:1.5;margin:8px 0 0 0;">%s</p>`, subtitle)
	}
	return fmt.Sprintf(`
      <div class="header" style="margin-bottom:24px;text-align:left;">
        <div class="header-pre" style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#71717a;margin-bottom:8px;">
          <span class="header-icon" style="margin-right:4px;">%s</span>%s · %s
        </div>
        <h1 class="header-title" style="font-size:22px;font-weight:800;color:#09090b;margin:0;line-height:1.25;letter-spacing:-0.5px;">%s</h1>
        %s
      </div>`, icon, brandName, category, title, subRow)
}

func (s *EmailService) htmlFooter(extraNote string) string {
	noteHTML := ""
	if extraNote != "" {
		noteHTML = fmt.Sprintf(`<p style="font-size:12px;color:#71717a;line-height:1.6;margin-bottom:16px;">%s</p>`, extraNote)
	}
	return fmt.Sprintf(`
          <hr class="divider" style="border:none;border-top:1px solid #e4e4e7;margin:28px 0;"/>
          <div class="footer" style="text-align:center;">
            %s
            <div class="badge" style="display:inline-block;margin-top:12px;font-size:11px;color:#a1a1aa;letter-spacing:.3px;">%s</div>
          </div>`, noteHTML, footerCredit)
}

func (s *EmailService) saveDevPreview(subject, toEmail, htmlBody, label string) string {
	dir := "email_previews"
	_ = os.MkdirAll(dir, 0755)
	ts := time.Now().Format("20060102_150405_000000")
	safeLabel := strings.ToLower(strings.ReplaceAll(label, " ", "_"))
	filename := fmt.Sprintf("%s_%s.html", ts, safeLabel)
	path := filepath.Join(dir, filename)
	_ = os.WriteFile(path, []byte(htmlBody), 0644)
	return path
}

func (s *EmailService) send(toEmail, subject, textBody, htmlBody, label string) {
	log.Printf("[email] dispatching %s to %s | subject: %s", label, toEmail, subject)

	if s.cfg.IsDevelopment() {
		previewPath := s.saveDevPreview(subject, toEmail, htmlBody, label)
		log.Printf("[email] [DEV] preview saved to %s", previewPath)
	}

	fromAddr := s.cfg.SMTPUsername
	if fromAddr == "" {
		fromAddr = "noreply@memo.sadguruchenu.in"
	}

	// 1. Try Gmail API if OAuth credentials exist
	if s.cfg.GmailClientID != "" && s.cfg.GmailClientSecret != "" && s.cfg.GmailRefreshToken != "" {
		go func() {
			err := s.sendViaGmailAPI(toEmail, fromAddr, subject, textBody, htmlBody)
			if err != nil {
				log.Printf("[email] Gmail API error: %v, attempting SMTP fallback", err)
				s.sendViaSMTP(toEmail, fromAddr, subject, htmlBody)
			} else {
				log.Printf("[email] successfully sent %s to %s via Gmail API", label, toEmail)
			}
		}()
		return
	}

	// 2. Try SMTP if configured
	if s.cfg.SMTPUsername != "" && s.cfg.SMTPPassword != "" {
		go func() {
			s.sendViaSMTP(toEmail, fromAddr, subject, htmlBody)
		}()
		return
	}

	log.Printf("[email] neither Gmail API nor SMTP credentials configured; email was not delivered")
}

func (s *EmailService) sendViaGmailAPI(toEmail, fromAddr, subject, textBody, htmlBody string) error {
	// Request refreshed access token using refresh token
	tokenURL := "https://oauth2.googleapis.com/token"
	data := url.Values{
		"client_id":     {s.cfg.GmailClientID},
		"client_secret": {s.cfg.GmailClientSecret},
		"refresh_token": {s.cfg.GmailRefreshToken},
		"grant_type":    {"refresh_token"},
	}

	resp, err := http.PostForm(tokenURL, data)
	if err != nil {
		return fmt.Errorf("refresh token request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("refresh token failed status %d: %s", resp.StatusCode, string(body))
	}

	var tr struct {
		AccessToken string `json:"access_token"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&tr); err != nil {
		return fmt.Errorf("decode access token: %w", err)
	}

	// Construct RFC 2822 email message
	boundary := "===MEMO_BOUNDARY==="
	rawMessage := fmt.Sprintf("From: %s\r\nTo: %s\r\nSubject: %s\r\nMIME-Version: 1.0\r\nContent-Type: multipart/alternative; boundary=%s\r\n\r\n"+
		"--%s\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n%s\r\n\r\n"+
		"--%s\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n%s\r\n\r\n"+
		"--%s--",
		fromAddr, toEmail, subject, boundary, boundary, textBody, boundary, htmlBody, boundary)

	// Gmail API expects raw message base64url-encoded
	b64 := strings.ReplaceAll(strings.ReplaceAll(bytes.NewBufferString(rawMessage).String(), "+", "-"), "/", "_")
	b64 = strings.TrimRight(b64, "=")

	sendURL := "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
	payload, _ := json.Marshal(map[string]string{"raw": b64})

	req, err := http.NewRequest(http.MethodPost, sendURL, bytes.NewBuffer(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+tr.AccessToken)
	req.Header.Set("Content-Type", "application/json")

	sendResp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer sendResp.Body.Close()

	if sendResp.StatusCode >= 300 {
		b, _ := io.ReadAll(sendResp.Body)
		return fmt.Errorf("send message failed (%d): %s", sendResp.StatusCode, string(b))
	}

	return nil
}

func (s *EmailService) sendViaSMTP(toEmail, fromAddr, subject, htmlBody string) {
	smtpHost := s.cfg.SMTPHost
	smtpPort := s.cfg.SMTPPort
	smtpUser := s.cfg.SMTPUsername
	smtpPass := s.cfg.SMTPPassword

	msg := fmt.Sprintf("From: %s\r\nTo: %s\r\nSubject: %s\r\nMIME-Version: 1.0\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n%s",
		fromAddr, toEmail, subject, htmlBody)

	auth := smtp.PlainAuth("", smtpUser, smtpPass, smtpHost)
	addr := fmt.Sprintf("%s:%s", smtpHost, smtpPort)

	if err := smtp.SendMail(addr, auth, smtpUser, []string{toEmail}, []byte(msg)); err != nil {
		log.Printf("[email] SMTP delivery failed to %s: %v", toEmail, err)
	} else {
		log.Printf("[email] SMTP email sent successfully to %s", toEmail)
	}
}

// SendOTPEmail sends verification OTP for Registration, Login, or Password Reset.
func (s *EmailService) SendOTPEmail(toEmail, otpCode string, purpose OTPPurpose) {
	subject := fmt.Sprintf("Your %s Verification Code", brandName)
	title := "Verification Code"
	subtitle := "Use the code below to continue."
	icon := "✅"

	switch purpose {
	case OTPRegister:
		subject = fmt.Sprintf("Verify your email for %s", brandName)
		title = fmt.Sprintf("Welcome to %s", brandName)
		subtitle = "Enter this verification code to complete your registration."
		icon = "✅"
	case OTPLogin:
		subject = fmt.Sprintf("Your %s sign-in code", brandName)
		title = fmt.Sprintf("Sign in to %s", brandName)
		subtitle = "Use the one-time code below to sign in securely."
		icon = "🔐"
	case OTPPasswordReset:
		subject = fmt.Sprintf("Reset your %s password", brandName)
		title = "Password Reset"
		subtitle = "Use the code below to reset your password. It expires in 10 minutes."
		icon = "🔑"
	}

	header := s.htmlHeader(icon, title, subtitle, "SECURITY")
	footer := s.htmlFooter("If you didn't request this, you can safely ignore this email.<br/>This is an automated message from " + brandName + ".")

	htmlBody := fmt.Sprintf(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="color-scheme" content="light dark"/>
<title>%s</title>
<style>%s</style>
</head>
<body>
<div class="wrap">
  <table width="100%%" role="presentation" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <div class="card">
        <div class="body">
          %s
          <div class="otp-wrap" style="text-align:center;">
            <div class="otp-label">Your one-time code</div>
            <div class="otp-box">%s</div>
          </div>
          <div class="note" style="text-align:center;">
            ⏱ This code expires in <strong>10 minutes</strong>.<br/>
            🔒 Never share this with anyone.
          </div>
          %s
        </div>
      </div>
    </td></tr>
  </table>
</div>
</body>
</html>`, subject, emailStyle, header, otpCode, footer)

	textBody := fmt.Sprintf("%s · %s\n\n%s\n\nYour OTP: %s\n\nThis code expires in 10 minutes. Do not share it with anyone.\n\n— Built by Sadguru (%s)",
		brandName, title, subtitle, otpCode, githubURL)

	s.send(toEmail, subject, textBody, htmlBody, "OTP Email")
}

// SendTaskReminderEmail sends notifications for due or recurring tasks.
func (s *EmailService) SendTaskReminderEmail(toEmail, taskTitle, taskDesc, taskUUID string, isRecurring bool) {
	title := "Task Reminder"
	icon := "✅"
	if isRecurring {
		title = "Recurring Task Reminder"
		icon = "🚨"
	}

	subject := fmt.Sprintf("%s: %s", title, taskTitle)
	base := strings.TrimRight(s.cfg.FrontendURL, "/")
	ctaURL := fmt.Sprintf("%s/tasks?task=%s", base, taskUUID)

	header := s.htmlHeader(icon, title, "", "REMINDER")
	footer := s.htmlFooter(fmt.Sprintf("You're receiving this because reminders are enabled in your %s settings.<br/>You can update your preferences anytime from the app.", brandName))

	descHTML := ""
	if taskDesc != "" {
		descHTML = fmt.Sprintf(`<p class="task-desc" style="font-size:14px;color:#52525b;line-height:1.6;margin:0;">%s</p>`, taskDesc)
	}

	contentBox := fmt.Sprintf(`
      <div class="content-box" style="background:#fafafa;border:1px solid #e4e4e7;border-left:3px solid #09090b;border-radius:8px;padding:20px;margin-bottom:20px;text-align:left;">
        <a href="%s" target="_blank" class="task-title" style="font-size:16px;font-weight:700;color:#09090b;text-decoration:none;line-height:1.35;display:block;word-break:break-word;margin-bottom:8px;">📌 %s</a>
        %s
        <div class="cta-btn-wrap" style="margin-top:16px;">
          <a href="%s" target="_blank" class="cta-btn" style="display:inline-block;padding:10px 20px;background:#09090b;color:#ffffff;font-size:13px;font-weight:600;border-radius:8px;text-decoration:none;letter-spacing:.2px;">Open Task →</a>
        </div>
      </div>`, ctaURL, taskTitle, descHTML, ctaURL)

	htmlBody := fmt.Sprintf(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="color-scheme" content="light dark"/>
<title>%s</title>
<style>%s</style>
</head>
<body>
<div class="wrap">
  <table width="100%%" role="presentation" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <div class="card">
        <div class="body">
          %s
          %s
          %s
        </div>
      </div>
    </td></tr>
  </table>
</div>
</body>
</html>`, subject, emailStyle, header, contentBox, footer)

	textBody := fmt.Sprintf("%s\n\n%s\n%s\n\nOpen in %s: %s\n\n— Built by Sadguru (%s) · %s",
		title, taskTitle, taskDesc, brandName, ctaURL, githubURL, brandName)

	s.send(toEmail, subject, textBody, htmlBody, "Task Reminder")
}

// SendJournalReminderEmail prompts the user to write their daily entry.
func (s *EmailService) SendJournalReminderEmail(toEmail string) {
	title := "Daily Journal Reminder"
	subtitle := "Don’t forget to write your progress!"
	bodyText := "Every day counts. Keep up the good work and jot down your thoughts today."
	icon := "📓"
	subject := "Daily Journal Reminder"

	base := strings.TrimRight(s.cfg.FrontendURL, "/")
	ctaURL := fmt.Sprintf("%s/journals/write", base)

	header := s.htmlHeader(icon, title, subtitle, "REMINDER")
	footer := s.htmlFooter(fmt.Sprintf("You're receiving this because daily journal reminders are enabled in your %s settings.<br/>You can update your preferences anytime from the app.", brandName))

	contentBox := fmt.Sprintf(`
      <div class="content-box" style="background:#fafafa;border:1px solid #e4e4e7;border-left:3px solid #09090b;border-radius:8px;padding:20px;margin-bottom:20px;text-align:left;">
        <p class="task-desc" style="font-size:14px;color:#52525b;line-height:1.6;margin:0 0 16px;">%s</p>
        <div class="cta-btn-wrap" style="margin-top:16px;">
          <a href="%s" target="_blank" class="cta-btn" style="display:inline-block;padding:10px 20px;background:#09090b;color:#ffffff;font-size:13px;font-weight:600;border-radius:8px;text-decoration:none;letter-spacing:.2px;">Write Today’s Journal →</a>
        </div>
      </div>`, bodyText, ctaURL)

	htmlBody := fmt.Sprintf(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="color-scheme" content="light dark"/>
<title>%s</title>
<style>%s</style>
</head>
<body>
<div class="wrap">
  <table width="100%%" role="presentation" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <div class="card">
        <div class="body">
          %s
          %s
          %s
        </div>
      </div>
    </td></tr>
  </table>
</div>
</body>
</html>`, subject, emailStyle, header, contentBox, footer)

	textBody := fmt.Sprintf("%s\n%s\n\n%s\n\nWrite in %s: %s\n\n— Built by Sadguru (%s) · %s",
		title, subtitle, bodyText, brandName, ctaURL, githubURL, brandName)

	s.send(toEmail, subject, textBody, htmlBody, "Journal Reminder")
}
