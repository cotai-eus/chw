// MongoDB initialization script
// This script runs when the MongoDB container starts for the first time

// Switch to the tender_platform database
db = db.getSiblingDB('tender_platform');

// Create application user
db.createUser({
  user: 'mongo_user',
  pwd: 'mongo_password',
  roles: [
    {
      role: 'readWrite',
      db: 'tender_platform'
    }
  ]
});

// Create collections with validation schemas
db.createCollection('notifications', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'type', 'title', 'message', 'created_at'],
      properties: {
        user_id: {
          bsonType: 'string',
          description: 'User ID is required'
        },
        type: {
          bsonType: 'string',
          enum: ['info', 'warning', 'error', 'success'],
          description: 'Notification type must be one of the enum values'
        },
        title: {
          bsonType: 'string',
          description: 'Title is required'
        },
        message: {
          bsonType: 'string',
          description: 'Message is required'
        },
        read: {
          bsonType: 'bool',
          description: 'Read status'
        },
        created_at: {
          bsonType: 'date',
          description: 'Created at timestamp is required'
        }
      }
    }
  }
});

db.createCollection('ai_processing_jobs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['job_id', 'document_id', 'user_id', 'company_id', 'status', 'created_at'],
      properties: {
        job_id: {
          bsonType: 'string',
          description: 'Job ID is required'
        },
        document_id: {
          bsonType: 'string',
          description: 'Document ID is required'
        },
        user_id: {
          bsonType: 'string',
          description: 'User ID is required'
        },
        company_id: {
          bsonType: 'string',
          description: 'Company ID is required'
        },
        status: {
          bsonType: 'string',
          enum: ['QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'],
          description: 'Status must be one of the enum values'
        },
        created_at: {
          bsonType: 'date',
          description: 'Created at timestamp is required'
        }
      }
    }
  }
});

db.createCollection('documents', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['document_id', 'tender_id', 'filename', 'file_type', 'uploaded_at'],
      properties: {
        document_id: {
          bsonType: 'string',
          description: 'Document ID is required'
        },
        tender_id: {
          bsonType: 'string',
          description: 'Tender ID is required'
        },
        filename: {
          bsonType: 'string',
          description: 'Filename is required'
        },
        file_type: {
          bsonType: 'string',
          description: 'File type is required'
        },
        uploaded_at: {
          bsonType: 'date',
          description: 'Upload timestamp is required'
        }
      }
    }
  }
});

// Create indexes
db.notifications.createIndex({ 'user_id': 1, 'created_at': -1 });
db.notifications.createIndex({ 'read': 1 });

db.ai_processing_jobs.createIndex({ 'job_id': 1 }, { unique: true });
db.ai_processing_jobs.createIndex({ 'document_id': 1 });
db.ai_processing_jobs.createIndex({ 'user_id': 1, 'created_at': -1 });
db.ai_processing_jobs.createIndex({ 'status': 1 });

db.documents.createIndex({ 'document_id': 1 }, { unique: true });
db.documents.createIndex({ 'tender_id': 1 });
db.documents.createIndex({ 'uploaded_at': -1 });

print('✅ MongoDB initialization completed successfully!');
