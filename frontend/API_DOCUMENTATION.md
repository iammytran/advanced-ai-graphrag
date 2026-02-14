# API Documentation

> **Note:** This project currently uses mock APIs (client-side JavaScript functions). The documentation below shows the structure as if these were real REST API endpoints for future backend integration.

---

## Base Configuration

- **Host:** `localhost:3000` (example for future backend)
- **Base URL:** `/api/v1`
- **Content-Type:** `application/json`
- **Accept:** `application/json`

---

## 1. Legal Chatbot API

### 1.1 Send Message

Ask a legal question and receive an answer based on character and tone preferences.

**Endpoint:**
```
POST /api/v1/chatbot/message
```

**Host:**
```
localhost:3000
```

**URL:**
```
http://localhost:3000/api/v1/chatbot/message
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```

**Request Body:**
```json
{
  "question": "Thuê nhà cần lưu ý gì?",
  "options": {
    "character": "lawyer",
    "toneValue": 80,
    "illustrationType": "comic"
  }
}
```

**Request Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `question` | String | Yes | - | The user's legal question |
| `options` | Object | No | - | Configuration options |
| `options.character` | String | No | `"normal"` | Character style: `"lawyer"` or `"normal"` |
| `options.toneValue` | Number | No | `50` | Tone control (0-100): 0=casual, 100=formal |
| `options.illustrationType` | String | No | `"none"` | Illustration type: `"none"`, `"comic"`, or `"poster"` |

**Response (200 OK):**
```json
{
  "text": "Theo quy định tại Điều 472 Bộ luật Dân sự 2015, hợp đồng thuê nhà ở là sự thỏa thuận giữa các bên...",
  "character": "lawyer",
  "timestamp": "2024-02-13T14:04:12.000Z",
  "illustration": {
    "type": "comic",
    "url": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&h=250&fit=crop",
    "caption": "📖 Minh họa truyện tranh - Dễ nhớ, dễ chia sẻ!"
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `text` | String | The answer text, blended based on tone value |
| `character` | String | The character that responded: `"lawyer"` or `"normal"` |
| `timestamp` | String | ISO 8601 timestamp of the response |
| `illustration` | Object | Optional - included when `illustrationType` is not `"none"` |
| `illustration.type` | String | Type of illustration: `"comic"` or `"poster"` |
| `illustration.url` | String | URL of the illustration image |
| `illustration.caption` | String | Caption text for the illustration |

---

### 1.2 Get Suggested Questions

Retrieve a list of suggested questions for users.

**Endpoint:**
```
GET /api/v1/chatbot/suggestions
```

**Host:**
```
localhost:3000
```

**URL:**
```
http://localhost:3000/api/v1/chatbot/suggestions
```

**Headers:**
```json
{
  "Accept": "application/json"
}
```

**Request Body:**
```
None (GET request)
```

**Response (200 OK):**
```json
{
  "suggestions": [
    "Thuê nhà cần lưu ý gì?",
    "Thủ tục ly hôn như thế nào?",
    "Bị tai nạn giao thông phải làm sao?",
    "Viết di chúc thế nào cho đúng?"
  ]
}
```

---

## 2. Virtual Courtroom API

### 2.1 Get Scenarios

Retrieve the list of available courtroom scenarios.

**Endpoint:**
```
GET /api/v1/courtroom/scenarios
```

**Host:**
```
localhost:3000
```

**URL:**
```
http://localhost:3000/api/v1/courtroom/scenarios
```

**Headers:**
```json
{
  "Accept": "application/json"
}
```

**Request Body:**
```
None (GET request)
```

**Response (200 OK):**
```json
{
  "scenarios": [
    {
      "id": 1,
      "name": "Tranh chấp hợp đồng thuê nhà",
      "difficulty": 1,
      "difficultyLabel": "Dễ",
      "duration": 15,
      "skills": ["Tranh luận cơ bản", "Thu thập chứng cứ"],
      "description": "Người thuê nhà yêu cầu bồi thường do chủ nhà vi phạm hợp đồng.",
      "summary": "Anh Minh thuê căn hộ của bà Hoa với thời hạn 1 năm...",
      "facts": [
        "Hợp đồng thuê nhà ký ngày 01/01/2024, thời hạn 12 tháng",
        "Tiền đặt cọc: 20 triệu đồng",
        "Tiền thuê hàng tháng: 10 triệu đồng"
      ]
    }
  ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | Number | Unique scenario identifier |
| `name` | String | Name of the legal case scenario |
| `difficulty` | Number | Difficulty level (1=Easy, 2=Medium, 3=Hard) |
| `difficultyLabel` | String | Human-readable difficulty label |
| `duration` | Number | Estimated duration in minutes |
| `skills` | Array[String] | Required legal skills for this scenario |
| `description` | String | Short description of the case |
| `summary` | String | Detailed case summary including parties and claims |
| `facts` | Array[String] | List of case facts/evidence |

---

### 2.2 Get Opponent Response

Submit an argument and receive a response from the AI opponent.

**Endpoint:**
```
POST /api/v1/courtroom/opponent-response
```

**Host:**
```
localhost:3000
```

**URL:**
```
http://localhost:3000/api/v1/courtroom/opponent-response
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```

**Request Body:**
```json
{
  "round": 1,
  "userArgument": "Căn cứ vào Điều 472 Bộ luật Dân sự 2015, bà Hoa đã vi phạm hợp đồng...",
  "scenario": {
    "id": 1,
    "name": "Tranh chấp hợp đồng thuê nhà"
  }
}
```

**Request Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `round` | Number | Yes | Current round number (affects response variety) |
| `userArgument` | String | Yes | The user's legal argument text |
| `scenario` | Object | Yes | The current case scenario object |
| `scenario.id` | Number | Yes | Scenario ID |
| `scenario.name` | String | Yes | Scenario name |

**Response (200 OK):**
```json
{
  "text": "Tôi phản đối lập luận này. Theo quy định pháp luật, bên nguyên đơn chưa cung cấp đủ bằng chứng để chứng minh thiệt hại thực tế.",
  "character": "opponent"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `text` | String | The opponent's rebuttal argument |
| `character` | String | Always `"opponent"` |

---

### 2.3 Get Coach Feedback

Request coaching feedback on your argument.

**Endpoint:**
```
POST /api/v1/courtroom/coach-feedback
```

**Host:**
```
localhost:3000
```

**URL:**
```
http://localhost:3000/api/v1/courtroom/coach-feedback
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```

**Request Body:**
```json
{
  "content": "Căn cứ vào Điều 472 Bộ luật Dân sự 2015...",
  "coachType": "lawyer",
  "tone": 75
}
```

**Request Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `content` | String | Yes | - | The user's argument content |
| `coachType` | String | No | `"normal"` | Coach style: `"lawyer"` or `"normal"` |
| `tone` | Number | No | `50` | Tone value (0-100) |

**Response (200 OK):**
```json
{
  "text": "Luận điểm này có căn cứ pháp lý vững chắc. Hãy bổ sung thêm điều luật cụ thể."
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `text` | String | Coaching feedback and advice |

---

### 2.4 Calculate Session Scores

Calculate performance scores for a completed courtroom session.

**Endpoint:**
```
POST /api/v1/courtroom/calculate-scores
```

**Host:**
```
localhost:3000
```

**URL:**
```
http://localhost:3000/api/v1/courtroom/calculate-scores
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```

**Request Body:**
```json
{
  "session": {
    "timeRemaining": 300,
    "arguments": [
      { "text": "Argument 1", "round": 1 },
      { "text": "Argument 2", "round": 2 }
    ],
    "evidences": [
      { "type": "contract", "description": "Hợp đồng thuê nhà" }
    ]
  }
}
```

**Request Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session` | Object | Yes | Session data object |
| `session.timeRemaining` | Number | Yes | Remaining time in seconds |
| `session.arguments` | Array[Object] | Yes | List of arguments made during session |
| `session.evidences` | Array[Object] | Yes | List of evidence presented |

**Response (200 OK):**
```json
{
  "scores": {
    "legalAccuracy": 85,
    "evidenceUse": 75,
    "persuasion": 80,
    "timeManagement": 90,
    "etiquette": 88
  },
  "totalScore": 418,
  "earnedBadges": ["excellent", "speed"]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `scores` | Object | Performance score breakdown |
| `scores.legalAccuracy` | Number | Legal accuracy score (0-100) |
| `scores.evidenceUse` | Number | Evidence usage score (0-100) |
| `scores.persuasion` | Number | Persuasiveness score (0-100) |
| `scores.timeManagement` | Number | Time management score (0-100) |
| `scores.etiquette` | Number | Courtroom etiquette score (0-100) |
| `totalScore` | Number | Sum of all scores |
| `earnedBadges` | Array[String] | List of badge IDs earned in this session |

---

### 2.5 Get Badges

Retrieve all available badges and user's earned badges.

**Endpoint:**
```
GET /api/v1/courtroom/badges
```

**Host:**
```
localhost:3000
```

**URL:**
```
http://localhost:3000/api/v1/courtroom/badges
```

**Headers:**
```json
{
  "Accept": "application/json"
}
```

**Request Body:**
```
None (GET request)
```

**Response (200 OK):**
```json
{
  "allBadges": [
    {
      "id": "excellent",
      "name": "Luật sư xuất sắc",
      "icon": "🥇",
      "description": "Tổng điểm > 400",
      "threshold": 400
    },
    {
      "id": "evidence",
      "name": "Bậc thầy chứng cứ",
      "icon": "📊",
      "description": "Evidence Use > 90",
      "threshold": 90
    }
  ],
  "userBadges": [
    {
      "id": "excellent",
      "count": 3,
      "lastEarned": "2024-02-13T14:04:12.000Z"
    }
  ]
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Invalid request parameters",
    "details": "The 'question' field is required"
  }
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "details": "Please try again later"
  }
}
```

---

## Currently Supported Topics (Mock Data)

The chatbot currently has detailed responses for:
- 🏠 **Thuê nhà** - Rental agreements
- 💔 **Ly hôn** - Divorce procedures
- 🚗 **Tai nạn giao thông** - Traffic accidents
- 📄 **Di chúc** - Wills and testaments

For other topics, a default response is provided.
