// MongoDB Schema for Notifications System
// Flexible notification storage with dynamic content and metadata

// Notifications Collection
db.createCollection("notifications", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["user_id", "company_id", "type", "title", "content", "created_at", "read", "priority"],
            properties: {
                _id: { bsonType: "objectId" },
                user_id: { bsonType: "string" },
                company_id: { bsonType: "string" },
                type: { 
                    bsonType: "string",
                    enum: ["system", "tender", "ai_analysis", "security", "workflow", "calendar", "message"]
                },
                category: { bsonType: "string" },
                title: { bsonType: "string", maxLength: 200 },
                content: { bsonType: "object" }, // Flexible content structure
                metadata: { bsonType: "object" }, // Additional context data
                actions: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        required: ["action_type", "label"],
                        properties: {
                            action_type: { bsonType: "string" },
                            label: { bsonType: "string" },
                            url: { bsonType: "string" },
                            api_endpoint: { bsonType: "string" },
                            parameters: { bsonType: "object" }
                        }
                    }
                },
                priority: { 
                    bsonType: "string",
                    enum: ["low", "medium", "high", "critical"]
                },
                read: { bsonType: "bool" },
                read_at: { bsonType: "date" },
                archived: { bsonType: "bool", default: false },
                archived_at: { bsonType: "date" },
                expires_at: { bsonType: "date" },
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" },
                source_entity: {
                    bsonType: "object",
                    properties: {
                        entity_type: { bsonType: "string" },
                        entity_id: { bsonType: "string" },
                        entity_data: { bsonType: "object" }
                    }
                },
                delivery_channels: {
                    bsonType: "array",
                    items: {
                        bsonType: "string",
                        enum: ["in_app", "email", "sms", "push", "webhook"]
                    }
                },
                delivery_status: {
                    bsonType: "object",
                    properties: {
                        in_app: { bsonType: "bool" },
                        email: { bsonType: "bool" },
                        sms: { bsonType: "bool" },
                        push: { bsonType: "bool" },
                        webhook: { bsonType: "bool" }
                    }
                }
            }
        }
    }
});

// Create indexes for notifications
db.notifications.createIndex({ "user_id": 1, "created_at": -1 });
db.notifications.createIndex({ "company_id": 1, "created_at": -1 });
db.notifications.createIndex({ "user_id": 1, "read": 1, "priority": -1 });
db.notifications.createIndex({ "type": 1, "created_at": -1 });
db.notifications.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
db.notifications.createIndex({ "archived": 1, "archived_at": 1 });
db.notifications.createIndex({ "source_entity.entity_type": 1, "source_entity.entity_id": 1 });

// Notification Templates Collection
db.createCollection("notification_templates", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["template_id", "name", "type", "content_template", "created_at"],
            properties: {
                _id: { bsonType: "objectId" },
                template_id: { bsonType: "string" },
                name: { bsonType: "string" },
                description: { bsonType: "string" },
                type: { bsonType: "string" },
                category: { bsonType: "string" },
                content_template: { bsonType: "object" },
                variables: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        required: ["name", "type"],
                        properties: {
                            name: { bsonType: "string" },
                            type: { bsonType: "string" },
                            required: { bsonType: "bool" },
                            default_value: {}
                        }
                    }
                },
                delivery_channels: {
                    bsonType: "array",
                    items: { bsonType: "string" }
                },
                priority: { bsonType: "string" },
                active: { bsonType: "bool", default: true },
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" },
                version: { bsonType: "int", default: 1 }
            }
        }
    }
});

db.notification_templates.createIndex({ "template_id": 1 }, { unique: true });
db.notification_templates.createIndex({ "type": 1, "active": 1 });
