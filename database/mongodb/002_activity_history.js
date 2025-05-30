// MongoDB Schema for Activity History and Timeline
// Flexible activity tracking across all system entities

// Activity History Collection
db.createCollection("activity_history", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["company_id", "entity_type", "entity_id", "action", "actor", "timestamp"],
            properties: {
                _id: { bsonType: "objectId" },
                company_id: { bsonType: "string" },
                entity_type: { 
                    bsonType: "string",
                    enum: ["tender", "supplier", "quote", "kanban_card", "document", "user", "company", "ai_analysis"]
                },
                entity_id: { bsonType: "string" },
                action: { 
                    bsonType: "string",
                    enum: ["created", "updated", "deleted", "viewed", "exported", "shared", "approved", "rejected", "commented", "analyzed"]
                },
                actor: {
                    bsonType: "object",
                    required: ["user_id", "user_name"],
                    properties: {
                        user_id: { bsonType: "string" },
                        user_name: { bsonType: "string" },
                        user_email: { bsonType: "string" },
                        ip_address: { bsonType: "string" },
                        user_agent: { bsonType: "string" }
                    }
                },
                changes: {
                    bsonType: "object",
                    properties: {
                        before: { bsonType: "object" },
                        after: { bsonType: "object" },
                        fields_changed: {
                            bsonType: "array",
                            items: { bsonType: "string" }
                        }
                    }
                },
                metadata: { bsonType: "object" },
                context: {
                    bsonType: "object",
                    properties: {
                        source: { bsonType: "string" },
                        workflow_step: { bsonType: "string" },
                        automation_trigger: { bsonType: "string" },
                        related_entities: {
                            bsonType: "array",
                            items: {
                                bsonType: "object",
                                properties: {
                                    entity_type: { bsonType: "string" },
                                    entity_id: { bsonType: "string" }
                                }
                            }
                        }
                    }
                },
                impact_score: { bsonType: "int", minimum: 1, maximum: 10 },
                tags: {
                    bsonType: "array",
                    items: { bsonType: "string" }
                },
                timestamp: { bsonType: "date" },
                expires_at: { bsonType: "date" }
            }
        }
    }
});

// Create indexes for activity history
db.activity_history.createIndex({ "company_id": 1, "timestamp": -1 });
db.activity_history.createIndex({ "entity_type": 1, "entity_id": 1, "timestamp": -1 });
db.activity_history.createIndex({ "actor.user_id": 1, "timestamp": -1 });
db.activity_history.createIndex({ "action": 1, "timestamp": -1 });
db.activity_history.createIndex({ "tags": 1 });
db.activity_history.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
db.activity_history.createIndex({ "impact_score": -1, "timestamp": -1 });

// User Timeline Collection (Aggregated view for quick access)
db.createCollection("user_timeline", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["user_id", "company_id", "timeline_data", "last_updated"],
            properties: {
                _id: { bsonType: "objectId" },
                user_id: { bsonType: "string" },
                company_id: { bsonType: "string" },
                timeline_data: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        required: ["date", "activities"],
                        properties: {
                            date: { bsonType: "string" }, // YYYY-MM-DD format
                            activities: {
                                bsonType: "array",
                                items: {
                                    bsonType: "object",
                                    properties: {
                                        activity_id: { bsonType: "objectId" },
                                        entity_type: { bsonType: "string" },
                                        entity_id: { bsonType: "string" },
                                        action: { bsonType: "string" },
                                        summary: { bsonType: "string" },
                                        timestamp: { bsonType: "date" },
                                        impact_score: { bsonType: "int" }
                                    }
                                }
                            },
                            activity_count: { bsonType: "int" },
                            top_entities: {
                                bsonType: "array",
                                items: {
                                    bsonType: "object",
                                    properties: {
                                        entity_type: { bsonType: "string" },
                                        entity_id: { bsonType: "string" },
                                        count: { bsonType: "int" }
                                    }
                                }
                            }
                        }
                    }
                },
                last_updated: { bsonType: "date" },
                expires_at: { bsonType: "date" }
            }
        }
    }
});

db.user_timeline.createIndex({ "user_id": 1, "company_id": 1 }, { unique: true });
db.user_timeline.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
