# Modern Random Chat Telegram Bot

A production-ready anonymous/random 1-on-1 chat Telegram bot built with Python, aiogram v3, and MongoDB. Features include gender-based matching, file sharing permissions, moderation tools, and a built-in monetization system.

## 🌟 Features

### Core Functionality
- **Random 1-on-1 Matching**: Queue-based system pairs users by gender preferences
- **Anonymous Chat**: No usernames or personal info shared between users
- **Gender Selection**: Male / Female / Other with flexible matching preferences
- **File Sharing**: Configurable per-user photo/file permissions
- **Session Management**: Skip, End, Report, and Block controls

### Monetization System
- **Deep-link Activation**: Users complete sponsor link visits every 12 hours
- **No Webhooks Required**: Uses Telegram deep-links for verification
- **Flexible Configuration**: Toggle globally or per-user
- **Token-based Verification**: Secure UUID tokens with expiration

### Moderation & Admin
- **Report System**: Users can report inappropriate behavior
- **Admin Controls**: Ban, warn, unban users
- **Broadcast Messages**: Reach all users instantly
- **Statistics Dashboard**: Track active users, sessions, monetization

### Privacy & Security
- **Fully Anonymous**: Users identified only by anonymous IDs
- **Blocking System**: Users can block unwanted contacts
- **Auto-cleanup**: Expired sessions automatically removed
- **No Chat History**: Messages forwarded in real-time, not stored

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/telegram-random-chat-bot.git
cd telegram-random-chat-bot
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start with Docker**
```bash
docker-compose up -d
```

4. **Check logs**
```bash
docker-compose logs -f bot
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token from BotFather | Required |
| `BOT_USERNAME` | Bot username (without @) | Required |
| `MONGODB_URI` | MongoDB connection string | `mongodb://mongodb:27017/randomchat` |
| `ADMIN_CHAT_ID` | Telegram user ID of admin | Required |
| `MONETIZE_ENABLED` | Enable monetization globally | `true` |
| `MONETIZE_INTERVAL_HOURS` | Hours between required visits | `12` |
| `MONETIZE_TOKEN_TTL_MINUTES` | Token expiration time | `30` |
| `MONETIZE_MIN_WAIT_SECONDS` | Minimum wait before confirmation | `10` |
| `SHORT_URL` | Sponsor link URL | `https://example.com` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Example .env
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
BOT_USERNAME=YourRandomChatBot
MONGODB_URI=mongodb://mongodb:27017/randomchat
ADMIN_CHAT_ID=123456789
MONETIZE_ENABLED=true
MONETIZE_INTERVAL_HOURS=12
MONETIZE_TOKEN_TTL_MINUTES=30
MONETIZE_MIN_WAIT_SECONDS=10
SHORT_URL=https://short.ly/yourlink
LOG_LEVEL=INFO
```

## 📚 User Guide

### Getting Started
1. Start the bot: `/start`
2. Complete onboarding:
   - Select your gender
   - Choose chat preference
   - Set file sharing permission
3. Find a partner: `/newchat`
4. Complete monetization challenge (every 12 hours)

### Commands
- `/start` - Start/restart the bot
- `/newchat` - Find a random chat partner
- `/end` - End current chat session
- `/profile` - View your profile
- `/settings` - Update preferences
- `/block <reason>` - Block current partner
- `/report <reason>` - Report inappropriate behavior
- `/help` - Show help message

### In-Chat Controls
- 🔁 **Skip** - Find new partner (ends current chat)
- ❌ **End** - End chat session
- 🚫 **Report** - Report current partner
- 📎 **Send File** - Send photo/file (if allowed)

### Monetization Flow
1. Every 12 hours, bot prompts monetization challenge
2. Click **🔗 Open Sponsor Link** → visit sponsor page
3. Click **✅ I've Completed** → deep-link activates bot
4. Bot verifies and unlocks features for next 12 hours

## 🛠️ Admin Commands

### User Management
- `/ban <user_id>` - Ban user from bot
- `/unban <user_id>` - Remove ban
- `/warn <user_id> <reason>` - Issue warning

### Monetization Control
- `/monetize_on` - Enable global monetization
- `/monetize_off` - Disable global monetization
- `/monetize_user_on <user_id>` - Enable for specific user
- `/monetize_user_off <user_id>` - Disable for specific user
- `/monetize_stats` - View monetization statistics

### System
- `/stats` - View bot statistics
- `/broadcast <message>` - Send message to all users

## 🏗️ Architecture

### Project Structure
```
telegram-random-chat-bot/
├── config/
│   └── settings.py          # Configuration management
├── database/
│   ├── mongodb.py           # MongoDB connection
│   └── models.py            # Data models
├── handlers/
│   ├── start.py             # Onboarding flow
│   ├── chat.py              # Chat session handling
│   ├── files.py             # File/media handling
│   ├── moderation.py        # Reports and blocking
│   ├── monetization.py      # Monetization system
│   └── admin.py             # Admin commands
├── utils/
│   ├── matching.py          # User matching logic
│   ├── session_manager.py   # Session management
│   ├── anonymizer.py        # Anonymization utilities
│   └── validators.py        # Input validation
├── middlewares/
│   └── auth.py              # Authentication middleware
├── main.py                  # Application entry point
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container definition
└── requirements.txt         # Python dependencies
```

### MongoDB Collections

#### `users`
Stores user profiles and preferences
```javascript
{
  tg_id: 123456789,              // Telegram user ID
  anon_id: "u_abc123",           // Anonymous identifier
  gender: "male",                 // male/female/other
  preference: "any",              // any/same/opposite/other
  consent_files: true,            // Allow receiving files
  blocked_users: [],              // List of blocked anon_ids
  is_banned: false,
  warnings: 0,
  monetize: {
    enabled: true,
    last_completed_at: ISODate(),
    next_due_at: ISODate()
  }
}
```

#### `sessions`
Active chat sessions
```javascript
{
  session_id: "sess_xyz",
  user1: {anon_id: "u_abc", tg_id: 111},
  user2: {anon_id: "u_def", tg_id: 222},
  started_at: ISODate(),
  status: "active",
  messages_count: 42
}
```

#### `monetize_tokens`
Monetization verification tokens
```javascript
{
  token: "uuid-v4",
  tg_id: 123456789,
  created_at: ISODate(),
  expires_at: ISODate(),
  status: "pending"  // pending/completed/expired
}
```

#### `settings`
Global configuration
```javascript
{
  _id: "global_settings",
  monetize_enabled: true,
  monetize_interval_hours: 12,
  short_url: "https://short.ly/xyz"
}
```

#### `reports`
User reports for moderation
```javascript
{
  reporter_anon_id: "u_abc",
  reported_anon_id: "u_def",
  session_id: "sess_xyz",
  reason: "spam",
  status: "pending"
}
```

### Key Components

#### Matching Algorithm
1. User enters queue with preferences
2. System searches for compatible partner
3. Validates both users' preferences match
4. Creates session and notifies both users
5. Routes messages between partners

#### Monetization System
1. Check if user's `next_due_at` has passed
2. Generate UUID token with TTL
3. Send challenge with sponsor link + deep-link
4. User visits sponsor, then clicks completion deep-link
5. Bot validates token and updates `next_due_at`

#### Anonymous Messaging
1. User A sends message
2. Bot looks up active session
3. Bot forwards to User B with User A's anon_id hidden
4. User B sees message as if from "Partner"

## 🧪 Development

### Local Setup (without Docker)

1. **Install Python 3.11+**
```bash
python3 --version
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start MongoDB locally**
```bash
# Using Docker for MongoDB only
docker run -d -p 27017:27017 --name mongo mongo:7
```

5. **Configure and run**
```bash
cp .env.example .env
# Edit .env
python main.py
```

### Testing

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python main.py

# Test with ngrok for webhook testing (optional)
ngrok http 8080
```

## 📊 Monitoring

### Logs
```bash
# View real-time logs
docker-compose logs -f bot

# View MongoDB logs
docker-compose logs -f mongodb
```

### Statistics
Use `/stats` command to view:
- Total registered users
- Active chat sessions
- Monetization completion rate
- Banned users count
- Total reports

## 🔒 Security Considerations

- **Anonymous IDs**: Generated using secure random methods
- **Token Security**: UUID v4 tokens with short TTL
- **No Data Storage**: Messages not persisted (privacy-first)
- **Rate Limiting**: Built into aiogram
- **Input Validation**: All user inputs sanitized
- **Admin Verification**: Commands check against ADMIN_CHAT_ID

## 🚀 Deployment

### Docker Compose (Recommended)
```bash
docker-compose up -d --build
```

### Cloud Platforms

#### Railway
1. Fork this repository
2. Create new project on Railway
3. Add MongoDB plugin
4. Add environment variables
5. Deploy from GitHub

#### Heroku
```bash
heroku create your-bot-name
heroku addons:create mongolab
heroku config:set BOT_TOKEN=your_token
git push heroku main
```

#### DigitalOcean
1. Create Droplet (Ubuntu 22.04)
2. Install Docker & Docker Compose
3. Clone repository
4. Configure .env
5. Run with docker-compose

## 🐛 Troubleshooting

### Bot doesn't respond
- Check `BOT_TOKEN` is correct
- Verify bot is running: `docker-compose ps`
- Check logs: `docker-compose logs bot`

### MongoDB connection failed
- Ensure MongoDB container is running
- Verify `MONGODB_URI` format
- Check network connectivity between containers

### Monetization not working
- Verify `BOT_USERNAME` matches actual bot username
- Check deep-link format in logs
- Ensure tokens haven't expired (check TTL)

### Users not matching
- Check gender preferences are compatible
- Verify queue has multiple users
- Review logs for matching errors

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## 📧 Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Email: your-email@example.com

## 🔮 Future Roadmap

- [ ] Interest-based matching
- [ ] Multi-user group chats
- [ ] In-chat translation
- [ ] VIP subscription (bypass monetization)
- [ ] Inline mode support
- [ ] Daily rewards/gamification
- [ ] Voice message support
- [ ] Advanced analytics dashboard
- [ ] Web admin panel

## 🙏 Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Telegram Bot framework
- [Motor](https://github.com/mongodb/motor) - Async MongoDB driver
- [MongoDB](https://www.mongodb.com/) - Database

---

**Made with ❤️ for the Telegram community**