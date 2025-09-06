# 🚀 Deploy Marketing Agents on Render

This guide will help you deploy Marketing Agents on Render in just a few minutes. Choose your deployment option:

## 🎯 Quick Start Options

### Option 1: Minimal Deploy (Fastest) ⚡
- **File:** `render-minimal.yaml`
- **Services:** Web + Database only
- **Time:** ~5 minutes
- **Features:** Basic app with core functionality
- **Best for:** Testing, demos, or getting started quickly

### Option 2: Full Deploy (Complete) 🔥
- **File:** `render.yaml`
- **Services:** Web + Worker + Database + Redis
- **Time:** ~10 minutes
- **Features:** Full functionality including background tasks
- **Best for:** Production use

## ✨ One-Click Deploy

### For Minimal Deploy:
1. **Fork this repository** to your GitHub account
2. **Rename `render-minimal.yaml` to `render.yaml`** in your fork
3. **Connect your GitHub account** to Render (if not already done)
4. **Create a new Blueprint** in Render:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Connect your forked repository
   - Render will automatically detect the `render.yaml` file

### For Full Deploy:
1. **Fork this repository** to your GitHub account
2. **Keep `render.yaml` as is** (full configuration)
3. **Create a new Blueprint** in Render (same steps as above)

## 🔧 Required Configuration

### For Minimal Deploy ⚡
**Only ONE API key required to get started:**
- **ANTHROPIC_API_KEY** - Get from [Anthropic Console](https://console.anthropic.com) ($5 credit included)

That's it! Your app will run with basic AI features. Add more APIs later as needed.

### For Full Deploy 🔥
**Essential API Keys (Required for core functionality):**

1. **ANTHROPIC_API_KEY** - Get from [Anthropic Console](https://console.anthropic.com)
2. **GEMINI_API_KEY** - Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
3. **PERPLEXITY_API_KEY** - Get from [Perplexity](https://perplexity.ai)

### 📧 Email Configuration (Required for user accounts)

1. **MAILGUN_API_KEY** - Sign up at [Mailgun](https://www.mailgun.com)
   - After signup, find your API key in the Mailgun dashboard

### 🗄️ File Storage (Required for media uploads)

Configure AWS S3 or compatible service:
1. **AWS_S3_ENDPOINT_URL** - Your S3 endpoint (e.g., `https://s3.amazonaws.com`)
2. **AWS_ACCESS_KEY_ID** - Your AWS access key
3. **AWS_SECRET_ACCESS_KEY** - Your AWS secret key

Alternative: Use [Backblaze B2](https://www.backblaze.com/b2/) or [DigitalOcean Spaces](https://www.digitalocean.com/products/spaces/) with S3-compatible endpoints.

### 🔍 SEO Features (Optional but recommended)

1. **JINA_READER_API_KEY** - Get from [Jina AI](https://jina.ai)
2. **KEYWORDS_EVERYWHERE_API_KEY** - Get from [Keywords Everywhere](https://keywordseverywhere.com/api)

### 💳 Payment Processing (Optional - for premium features)

1. **STRIPE_TEST_SECRET_KEY** - Get from [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys)
2. **STRIPE_LIVE_SECRET_KEY** - Get from [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
3. **DJSTRIPE_WEBHOOK_SECRET** - Stripe webhook endpoint secret

### 🔐 GitHub OAuth (Optional - for GitHub login)

1. **GITHUB_CLIENT_ID** - Create GitHub OAuth App in [GitHub Settings](https://github.com/settings/applications/new)
2. **GITHUB_CLIENT_SECRET** - From your GitHub OAuth App

### 📊 Monitoring (Optional)

1. **SENTRY_DSN** - Get from [Sentry](https://sentry.io)
2. **POSTHOG_API_KEY** - Get from [PostHog](https://posthog.com)

## 📝 Step-by-Step Setup

### 1. Deploy the Blueprint

1. In Render Dashboard, click "New" → "Blueprint"
2. Connect your forked repository
3. Click "Apply Blueprint"
4. Wait for the initial deployment to complete (this may take 5-10 minutes)

### 2. Configure Environment Variables

1. Go to your deployed web service in Render Dashboard
2. Click "Environment"
3. Update the placeholder values with your actual API keys and configuration
4. Click "Save Changes"

### 3. Trigger Redeploy

1. In your service dashboard, click "Manual Deploy"
2. Select "Deploy latest commit"
3. Wait for the deployment to complete

### 4. Create Superuser (Admin Access)

1. Go to your service dashboard
2. Click on "Shell" tab
3. Run this command to create an admin user:
   ```bash
   python manage.py createsuperuser
   ```
4. Follow the prompts to create your admin account

## 🎉 Your App is Live!

Your Marketing Agents app should now be running at your Render URL (e.g., `https://your-app-name.onrender.com`).

### Access Admin Panel
Visit `https://your-app-name.onrender.com/admin` to access the Django admin panel.

## 🚀 Minimal Setup (Get Started Fast)

If you want to get started quickly with minimal configuration:

1. **Required minimum:**
   - ANTHROPIC_API_KEY (for AI features)
   - MAILGUN_API_KEY (for user emails)
   - AWS S3 configuration (for file storage)

2. **Everything else can be added later** as you expand your usage of the app.

## 🔧 Troubleshooting

### Common Issues:

1. **Static files not loading?**
   - Make sure the build completed successfully
   - Check that `npm run build` ran without errors

2. **Database connection errors?**
   - Ensure the PostgreSQL database is fully provisioned
   - Check that DATABASE_URL is correctly set

3. **Email not working?**
   - Verify your MAILGUN_API_KEY is correct
   - Check Mailgun dashboard for sending domain verification

4. **AI features not working?**
   - Verify your API keys are correctly set
   - Check service logs for specific error messages

### Getting Help

- Check the [Render documentation](https://render.com/docs)
- Review the service logs in your Render dashboard
- Open an issue in this repository

## 📚 What's Included

Your deployment includes:
- ✅ Django web application
- ✅ PostgreSQL database
- ✅ Redis for background tasks
- ✅ Automatic SSL certificates
- ✅ Static file serving
- ✅ Health checks and monitoring

## 💡 Pro Tips

1. **Environment Variables**: Use Render's environment variable groups for better organization
2. **Monitoring**: Set up Sentry for error tracking in production
3. **Backups**: Render automatically backs up your PostgreSQL database
4. **Custom Domain**: You can add your own domain in the Render dashboard
5. **Scaling**: Upgrade your plan as your usage grows

---

Happy deploying! 🎉 Your Marketing Agents app will be live in just a few minutes.
