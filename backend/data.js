const case1 = {
  "date": "2026-03-21T10:00:00",
  "content": "Today was a calm and productive day.",
  "sections": []
}

const case2=
{
  "date": "2026-03-21T18:30:00",
  "content": "Reflecting on my day and planning ahead.",
  "sections": [
    {
      "name": "Morning Reflection",
      "template_id": null,
      "reusable": true,
      "field_values": [
        {
          "label": "How did I feel this morning?",
          "field_type": "text",
          "value": "Energetic and positive"
        },
        {
          "label": "Main goal for today",
          "field_type": "text",
          "value": "Finish backend optimization"
        }
      ]
    },
    {
      "name": "Work Progress",
      "template_id": null,
      "reusable": true,
      "field_values": [
        {
          "label": "What did I accomplish?",
          "field_type": "textarea",
          "value": "Optimized database queries and improved API performance."
        },
        {
          "label": "Any blockers?",
          "field_type": "text",
          "value": "Minor debugging issues"
        }
      ]
    },
    {
      "name": "Daily Habits",
      "template_id": null,
      "reusable": true,
      "field_values": [
        {
          "label": "Did I exercise?",
          "field_type": "checkbox",
          "value": "true"
        },
        {
          "label": "Did I read a book?",
          "field_type": "checkbox",
          "value": "false"
        }
      ]
    }
  ]
}


const case3=
{
  "date": "2026-03-22T08:00:00",
  "content": "Daily reflection and work updates.",
  "sections": [
    {
      "name": "Morning Reflection",
      "template_id": 7,
      "reusable": false,
      "field_values": [
        {
          "label": "How did I feel this morning?",
          "field_type": "text",
          "value": "Motivated and focused"
        },
        {
          "label": "Main goal for today",
          "field_type": "text",
          "value": "Finish FastAPI journaling module"
        }
      ]
    },
    {
      "name": "Work Progress",
      "template_id": 8,
      "reusable": false,
      "field_values": [
        {
          "label": "What did I accomplish?",
          "field_type": "textarea",
          "value": "Deployed optimized queries and added tests"
        },
        {
          "label": "Any blockers?",
          "field_type": "text",
          "value": "Waiting for API review feedback"
        }
      ]
    },
    {
      "name": "Daily Habits",
      "template_id": 9,
      "reusable": false,
      "field_values": [
        {
          "label": "Did I exercise?",
          "field_type": "checkbox",
          "value": "true"
        },
        {
          "label": "Did I read a book?",
          "field_type": "checkbox",
          "value": "false"
        }
      ]
    }
  ]
}


const case4 = {
  "date": "2026-03-22T09:30:00",
  "content": "Reflections and new tasks.",
  "sections": [
    {
      "name": "Morning Reflection",
      "template_id": 10,
      "reusable": false,
      "field_values": [
        {
          "label": "How did I feel this morning?",
          "field_type": "text",
          "value": "Motivated and positive"
        },
        {
          "label": "Main goal for today",
          "field_type": "text",
          "value": "Finish unit testing"
        }
      ]
    },
    {
      "name": "Work Progress",
      "template_id": 11,
      "reusable": false,
      "field_values": [
        {
          "label": "What did I accomplish?",
          "field_type": "textarea",
          "value": "Implemented caching for queries"
        },
        {
          "label": "Any blockers?",
          "field_type": "text",
          "value": "None"
        }
      ]
    },
    {
      "name": "Daily Habits",
      "template_id": 12,
      "reusable": false,
      "field_values": [
        {
          "label": "Did I exercise?",
          "field_type": "checkbox",
          "value": "true"
        },
        {
          "label": "Did I read a book?",
          "field_type": "checkbox",
          "value": "true"
        }
      ]
    },
    {
      "name": "Evening Reflection",
      "template_id": null,         
      "reusable": true,
      "field_values": [
        {
          "label": "What went well today?",
          "field_type": "textarea",
          "value": "Completed journaling API integration"
        },
        {
          "label": "What can be improved?",
          "field_type": "textarea",
          "value": "Handle empty field cases more gracefully"
        }
      ]
    }
  ]
}


// 
const getJournalDataList = 
  [
  {
    "date": "2026-03-21T18:30:00",
    "content": "Reflecting on my day and planning ahead.",
    "id": 6,
    "user_id": 1,
    "created_at": "2026-03-21T18:41:53.287843Z"
  }
]

const getJournalDetaislDataBasedOnId = {
  "id": 6,
  "date": "2026-03-21T18:30:00",
  "content": "Reflecting on my day and planning ahead.",
  "sections": [
    {
      "id": 16,
      "name": "Morning Reflection",
      "template_id": 10,
      "field_values": [
        {
          "id": 37,
          "label": "How did I feel this morning?",
          "field_type": "text",
          "value": "Energetic and positive"
        },
        {
          "id": 38,
          "label": "Main goal for today",
          "field_type": "text",
          "value": "Finish backend optimization"
        }
      ]
    },
    {
      "id": 17,
      "name": "Work Progress",
      "template_id": 11,
      "field_values": [
        {
          "id": 39,
          "label": "What did I accomplish?",
          "field_type": "textarea",
          "value": "Optimized database queries and improved API performance."
        },
        {
          "id": 40,
          "label": "Any blockers?",
          "field_type": "text",
          "value": "Minor debugging issues"
        }
      ]
    },
    {
      "id": 18,
      "name": "Daily Habits",
      "template_id": 12,
      "field_values": [
        {
          "id": 41,
          "label": "Did I exercise?",
          "field_type": "checkbox",
          "value": "true"
        },
        {
          "id": 42,
          "label": "Did I read a book?",
          "field_type": "checkbox",
          "value": "false"
        }
      ]
    }
  ]
}



const journalTemplates = {}