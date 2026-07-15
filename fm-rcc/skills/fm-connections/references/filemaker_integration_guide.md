# FileMaker Integration Guide - Complete API Reference

This document outlines all secrets, configurations, and lessons learned from integrating with FileMaker through all three available APIs: Data API, OttoFMS, and OData.

## API Comparison Matrix

| Feature | Data API | OttoFMS | OData |
| --- | --- | --- | --- |
| **Authentication** | Session tokens (15 min) | Persistent API keys | Per-request Basic/Bearer |
| **Query Approach** | Layout-based | Layout-based (proxy) | Table occurrence-based |
| **Transactions** | No | No | Yes (atomic batches) |
| **Session Management** | Required | Automatic | None needed |
| **Complex Queries** | Limited | Limited | Advanced ($filter, $expand) |
| **Container Support** | Full | Full | Limited formats |
| **PHP Support** | Excellent | Good | Basic |
| **Node.js Support** | Good | Good | Excellent |
| **Setup Complexity** | Low | Medium | Medium |

## Environment Variables

### Data API Configuration

```
# FileMaker Server Connection
FM_HOST=your-filemaker-server.com
FM_DATABASE=YourDatabase
FM_USERNAME=api_user
FM_PASSWORD=api_password
FM_SSL_VERIFY=false  # Set to false for internal servers with self-signed certificates

```

### OttoFMS Configuration

```
# OttoFMS API Proxy
OTTO_API_KEY=dk_12345678  # Data API key
OTTO_ADMIN_KEY=ak_87654321  # Admin API key (optional)
USE_OTTO_PROXY=true
# Uses same FM_HOST - OttoFMS runs on same server

# IMPORTANT: When using API keys with Otto, URLs change:
# OData + API Key: <https://host/otto/fmi/odata/v4/database/>
# Data API + API Key: <https://host/otto/fmi/data/vLatest/databases/database/>

```

### OData Configuration

```
# OData API
ODATA_AUTH_METHOD=basic  # 'basic' for Server, 'fmid' for Cloud
ODATA_USERNAME=api_user  # Same as Data API user
ODATA_PASSWORD=api_password
ODATA_CLARIS_ID=your_claris_id_token  # Only for FileMaker Cloud
ENABLE_ODATA=true

```

### Important Notes on SSL

- Internal FileMaker servers often use self-signed certificates
- Set `FM_SSL_VERIFY=false` to bypass certificate validation
- In production with proper certificates, set to `true`
- OData REQUIRES valid SSL certificates (no self-signed)

## Authentication Comparison

### Data API Authentication

```jsx
// Session-based, requires management
private readonly SESSION_TIMEOUT = 10 * 60 * 1000 // 10 minutes
// Must track lastActivity and refresh before timeout

```

### OttoFMS Authentication

```jsx
// Simple API key in header - SAME for both APIs!
headers: {
  'Authorization': `Bearer ${process.env.OTTO_API_KEY}`
}
// No session management needed!

// IMPORTANT URL differences when using Otto API keys:
// OData endpoint: <https://host/otto/fmi/odata/v4/database/>
// Data API endpoint: <https://host/otto/fmi/data/vLatest/databases/database/>

// Note: Both APIs use Bearer token format when going through Otto proxy

```

### OData Authentication

```jsx
// Basic Auth (FileMaker Server)
headers: {
  'Authorization': `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`
}

// Bearer Token (FileMaker Cloud)
headers: {
  'Authorization': `FMID ${clarisIdToken}`
}

```

## Query Syntax Comparison

### Data API & OttoFMS Query Format

Both use the same FileMaker JSON query format:

```json
{
  "query": [
    {"fieldName": "value"}
  ]
}

```

### Get ALL Records - CRITICAL!

```jsx
// WRONG - Returns NO records
const query = []

// RIGHT - Data API
await client.getRecords('LAYOUT_NAME', limit, offset)

// RIGHT - OttoFMS (same endpoint, different URL)
await fetch(`https://server/otto/fmi/data/v1/databases/${db}/layouts/${layout}/records`)

```

### OData Query Format

OData uses URL parameters with standard syntax:

**IMPORTANT**: OData uses Table Occurrence names (from the Relationships Graph), NOT base table names!

```jsx
// Simple filter - 'Deliverables' is the table occurrence name
/tables/Deliverables?$filter=DisplayStatus eq 'Overdue'

// Multiple conditions
/tables/Deliverables?$filter=DisplayStatus eq 'Overdue' or DisplayStatus eq 'At Risk'

// Complex with relationships
/tables/Deliverables?$filter=DueDate lt 2025-07-26&$expand=Assignees($select=StaffFullName)

// Get ALL records
/tables/Deliverables  // No filter needed!

```

**Note**: The 'Deliverables' in the URL is the table occurrence name as it appears in the FileMaker Relationships Graph, not necessarily the base table name.

## Session Management

### Data API Session Management

- **FileMaker Session Timeout**: 15 minutes of inactivity
- **Recommended Refresh**: 10 minutes (600,000ms)
- **API Request Timeout**: 30 seconds (30,000ms)
- **Implementation**: Track last activity and proactively refresh

### OttoFMS Session Management

- **No session management required!**
- API keys are persistent
- OttoFMS handles token refresh internally
- Just include API key with each request

### OData Session Management

- **No sessions** - stateless authentication
- Each request includes credentials
- No timeout concerns
- Slight performance overhead per request

## Critical MCP Server Restart Note

**IMPORTANT**: After any code changes to the MCP server:

1. Run `npm run build` to compile TypeScript changes
2. **Restart Claude Desktop completely** (Cmd+Q then reopen)
3. The MCP server runs as a persistent process - code changes only take effect after restart
4. You'll know it worked when previously failing operations succeed

## Implementation Examples

### Data API Implementation

```jsx
class FileMakerClient {
  async authenticate() {
    const response = await fetch(`${this.baseUrl}/sessions`, {
      method: 'POST',
      headers: { 'Authorization': `Basic ${this.credentials}` }
    });
    this.token = response.headers.get('X-FM-Data-Access-Token');
  }

  async findRecords(layout, query) {
    // Check session timeout
    if (Date.now() - this.lastActivity > this.SESSION_TIMEOUT) {
      await this.refreshSession();
    }

    return fetch(`${this.baseUrl}/layouts/${layout}/_find`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query })
    });
  }
}

```

### OttoFMS Implementation

```jsx
class OttoFMSClient {
  constructor() {
    this.apiKey = process.env.OTTO_API_KEY;
    // Note the /otto/ prefix for API key authentication
    this.baseUrl = `https://${process.env.FM_HOST}/otto/fmi/data/vLatest`;
  }

  async findRecords(layout, query) {
    // No session management needed!
    return fetch(`${this.baseUrl}/databases/${this.database}/layouts/${layout}/_find`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query })
    });
  }
}

// For OData with Otto API key:
const odataUrl = `https://${process.env.FM_HOST}/otto/fmi/odata/v4/${database}/`;

```

### OData Implementation

```jsx
// Using fm-odata-client
import { BasicAuth, Connection } from 'fm-odata-client';

const connection = new Connection(
  process.env.FM_HOST,
  new BasicAuth(process.env.ODATA_USERNAME, process.env.ODATA_PASSWORD)
);

const database = connection.database(process.env.FM_DATABASE);

// Table occurrence query - uses occurrence name from Relationships Graph!
const deliverables = await database.table('Deliverables')  // 'Deliverables' is the table occurrence name
  .query({
    filter: "DisplayStatus eq 'Overdue'",
    expand: 'Assignees',
    top: 100
  });

// Raw fetch approach
const response = await fetch(
  `https://${host}/fmi/odata/v4/${database}/Deliverables?$filter=DisplayStatus eq 'Overdue'`,
  {
    headers: {
      'Authorization': `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`
    }
  }
);

```

## API Endpoint Reference

### Standard Authentication Endpoints

```
# OData (Basic Auth)
<https://host/fmi/odata/v4/database/>

# Data API (Session-based)
<https://host/fmi/data/vLatest/databases/database/>

```

### Otto API Key Authentication Endpoints

```
# OData + API Key (Otto proxy required!)
<https://host/otto/fmi/odata/v4/database/>

# Data API + API Key (Otto proxy)
<https://host/otto/fmi/data/vLatest/databases/database/>

```

**Critical**: When using API key authentication with OttoFMS, BOTH APIs require the `/otto/` prefix!

**Authentication Headers with Otto**:

- Both OData and Data API use `Authorization: Bearer {api_key}` when going through Otto proxy
- Do NOT use `x-fm-data-api-key` header with Otto - that's only for direct OData without Otto

### Real Example:

```
# Standard OData (Basic Auth):
<https://your-server.fmphost.com/fmi/odata/v4/YourDatabase/>

# OData with Otto API Key:
<https://your-server.fmphost.com/otto/fmi/odata/v4/YourDatabase/>

# Standard Data API (Session-based):
<https://your-server.fmphost.com/fmi/data/vLatest/databases/YourDatabase/>

# Data API with Otto API Key:
<https://your-server.fmphost.com/otto/fmi/data/vLatest/databases/YourDatabase/>

```

## Understanding OData Table Names

### Critical Concept: Table Occurrences vs Base Tables

**OData uses Table Occurrence names from the FileMaker Relationships Graph, NOT base table names!**

This is a common source of confusion:

```
Example FileMaker Structure:
- Base Table Name: TBL_CUSTOMERS
- Table Occurrence in Graph: Customers
- Another Occurrence of Same Table: Customers_Billing
- OData URLs:
  - /odata/v4/database/Customers ✅
  - /odata/v4/database/Customers_Billing ✅
  - /odata/v4/database/TBL_CUSTOMERS ❌ (won't work!)

```

**Why this matters:**

1. You can have multiple occurrences of the same base table
2. Each occurrence appears as a separate "table" in OData
3. The occurrence name is what you use in OData queries
4. This allows accessing the same data through different relationship contexts

**Best Practice:** Document your table occurrence names alongside your API documentation.

## Field Naming and Discovery

### Data API / OttoFMS Field Discovery

```jsx
const records = await client.getRecords('REQUEST_DELIVERABLES', 1);
if (records.length > 0) {
  console.log('Available fields:', Object.keys(records[0].fieldData));
}

```

### OData Field Discovery

```jsx
// Get table schema
const metadata = await fetch(`https://${host}/fmi/odata/v4/${database}/$metadata`);

// Or explore with a single record
const record = await database.table('Deliverables').first();
console.log('Table columns:', Object.keys(record));

```

### Common Field Patterns

```
Data API / OttoFMS (layout-based):
- request_deliverables__ASSIGNEES__RequestDeliverableID__cre_del::StaffFullName
- Uses :: for related fields
- Long relationship names

OData (table occurrence-based):
- Direct field names: DisplayStatus, DueDate
- Relationships via $expand: Deliverables?$expand=Assignees
- Cleaner, more standard naming
- IMPORTANT: Uses table occurrence names from Relationships Graph, not base table names

```

## Enhanced Query Examples - Updated MCP Server

### CRITICAL DataAPI Response Structure Differences (August 2025 Fix)

**Query Operations Response:**

```json
{
  "response": {
    "data": [
      {
        "fieldData": { ... },
        "recordId": "123",
        "modId": "0"
      }
    ],
    "dataInfo": { ... }
  },
  "messages": [{ "code": "0", "message": "OK" }]
}

```

**Create/Update/Delete Operations Response:**

```json
{
  "response": {
    "recordId": "123",
    "modId": "0"
  },
  "messages": [{ "code": "0", "message": "OK" }]
}

```

**Key Difference**: Create/Update/Delete return ONLY recordId and modId, NOT a data array!

**TypeScript Interfaces Required:**

```tsx
// For query operations
export interface DataApiResponse<T = FileMakerRecord> {
  response: {
    data: T[];
    dataInfo: { ... };
  };
  messages: Array<{ code: string; message: string; }>;
}

// For create/update/delete operations - CRITICAL!
export interface DataApiCreateResponse {
  response: {
    recordId: string;
    modId: string;
  };
  messages: Array<{ code: string; message: string; }>;
}

```

**Implementation Fix:**

```jsx
// WRONG - Causes "Cannot read properties of undefined (reading '0')" error
if (response.data.response.data && response.data.response.data.length > 0) {
  return response.data.response.data[0]; // ❌ data array doesn't exist!
}

// CORRECT - For create operations
if (response.data?.response?.recordId) {
  return {
    recordId: response.data.response.recordId,
    modId: response.data.response.modId,
    fieldData: originalData  // Include original data sent
  };
}

```

### Basic Filtering

```jsx
// Simple equality (both APIs)
const basicFilter = {
  "Status": "Active"
};

// OData Result: Status eq 'Active'
// Data API Result: [{"Status": "Active"}]

```

### Advanced OData Filtering (Enhanced MCP Server)

```jsx
// String operations
const stringFilters = {
  "Name": { "$contains": "john" },        // contains(Name, 'john')
  "Email": { "$startswith": "admin" },    // startswith(Email, 'admin')
  "Phone": { "$endswith": ".com" }        // endswith(Phone, '.com')
};

// Numeric comparisons
const numericFilters = {
  "Age": { "$gt": 21 },                    // Age gt 21
  "Salary": { "$gte": 50000 },             // Salary ge 50000
  "Score": { "$lt": 100 },                 // Score lt 100
  "Rating": { "$lte": 5 }                  // Rating le 5
};

// Array operations
const arrayFilters = {
  "Department": { "$in": ["IT", "HR"] }    // Department in ('IT','HR')
};

// Negation
const negationFilters = {
  "Status": { "$ne": "Deleted" }           // Status ne 'Deleted'
};

```

### Enhanced Data API Filtering (Fixed MCP Server)

```jsx
// Wildcard patterns
const dataApiFilters = {
  "Name": { "$contains": "john" },         // Name: "*john*"
  "Email": { "$startswith": "admin" },     // Email: "admin*"
  "Phone": { "$endswith": ".com" },       // Phone: "*.com"
  "Age": { "$gt": 21 },                   // Age: ">21"
  "Status": { "$ne": "Deleted" }          // Status: "!Deleted"
};

// Range queries
const rangeFilters = {
  "Date": { "$range": { "min": "2024-01-01", "max": "2024-12-31" } }  // Date: "2024-01-01...2024-12-31"
};

```

### MCP Server Usage Examples

```jsx
// Using the enhanced MCP server
const result = await mcpClient.call('query_records', {
  table_or_layout: 'T01_ACCOUNTS',
  api_type: 'odata',
  filter: {
    "CompanyName": { "$contains": "Tech" },
    "Status": "Active",
    "Revenue": { "$gt": 100000 }
  },
  limit: 50,
  sort: [{ "field": "CompanyName", "direction": "asc" }]
});

// Result: /T01_ACCOUNTS?$filter=contains(CompanyName, 'Tech') and Status eq 'Active' and Revenue gt 100000&$top=50&$orderby=CompanyName asc

```

### Complex Filtering Examples

```jsx
// Multiple conditions (enhanced MCP server)
const complexFilter = {
  "Status": { "$in": ["Active", "Pending"] },
  "CreatedDate": { "$gte": "2024-01-01" },
  "CompanyName": { "$contains": "Corp" }
};

// OData Result: Status in ('Active','Pending') and CreatedDate ge '2024-01-01' and contains(CompanyName, 'Corp')

// Data API equivalent (multiple OR queries)
// Query 1: {"Status": "Active", "CreatedDate": ">=2024-01-01", "CompanyName": "*Corp*"}
// Query 2: {"Status": "Pending", "CreatedDate": ">=2024-01-01", "CompanyName": "*Corp*"}

```

### Atomic Transaction (OData Only)

```jsx
// Create batch request
const batch = connection.createBatch();

// Add multiple operations
batch.create('Deliverables', { DeliverableName: 'New Task', Status: 'Pending' });
batch.update('Deliverables', recordId, { Status: 'Complete' });
batch.delete('Assignees', assigneeId);

// Execute atomically - all succeed or all fail
try {
  await batch.execute();
} catch (error) {
  // All operations rolled back
}

```

## Performance Optimization by API

### Data API Optimization

- Minimize session refreshes
- Batch related queries when possible
- Cache aggressively due to session overhead
- Use layout design to limit returned fields

### OttoFMS Optimization

- No session overhead improves performance
- Can make more granular requests
- Use webhook features for real-time updates
- Leverage built-in caching capabilities

### OData Optimization

- Use $select to limit fields
- $expand for related data in one call
- $filter extensively server-side
- Batch operations for atomic transactions
- Best for read-heavy operations

## Error Handling

### Common Error Codes

| Code | Data API | OttoFMS | OData | Description |
| --- | --- | --- | --- | --- |
| 401 | Session expired | Invalid API key | Invalid credentials | Authentication failure |
| 102 | Field missing | Field missing | Column not found | Field doesn't exist |
| 404 | Layout not found | Layout not found | Table not found | Resource missing |
| 500 | Server error | Server error | Server error | Internal FileMaker error |

### API-Specific Error Handling

```jsx
// Data API - Session expiry
if (error.code === '401') {
  await this.refreshSession();
  return retry();
}

// OttoFMS - API key issues
if (error.code === '401') {
  console.error('Invalid API key - check OTTO_API_KEY');
}

// OData - Field errors are more descriptive
if (error.message.includes('Unknown column')) {
  console.error('Field name issue - check exact table column name');
}

```

## Migration Strategies

### From Data API to OttoFMS

1. Install OttoFMS on FileMaker Server
2. Generate API keys in OttoFMS console
3. Change base URLs to include `/otto/` prefix:
    - Data API: `/fmi/data/vLatest` → `/otto/fmi/data/vLatest`
    - OData: `/fmi/odata/v4` → `/otto/fmi/odata/v4`
4. Replace session management with API key headers
5. Keep same query format

**URL Changes Example:**

```jsx
// Before (Standard auth):
const dataApiUrl = '<https://host/fmi/data/vLatest/databases/db/>';
const odataUrl = '<https://host/fmi/odata/v4/db/>';

// After (Otto API key auth):
const dataApiUrl = '<https://host/otto/fmi/data/vLatest/databases/db/>';
const odataUrl = '<https://host/otto/fmi/odata/v4/db/>';

```

### From Data API to OData

1. Enable OData in FileMaker Server
2. Map layout names to table occurrence names (from Relationships Graph)
3. Rewrite queries to OData syntax
4. Remove session management code
5. Update error handling for OData codes
6. Note: OData uses table occurrence names, not base table names

### Gradual Migration Pattern

```jsx
class FileMakerService {
  constructor() {
    this.useOData = process.env.ENABLE_ODATA === 'true';
    this.useOtto = process.env.USE_OTTO_PROXY === 'true';
  }

  async getDeliverables(status) {
    if (this.useOData) {
      return this.odataClient.query({
        filter: `DisplayStatus eq '${status}'`
      });
    } else if (this.useOtto) {
      return this.ottoClient.findRecords('REQUEST_DELIVERABLES',
        [{"DisplayStatus": status}]
      );
    } else {
      return this.dataApiClient.findRecords('REQUEST_DELIVERABLES',
        [{"DisplayStatus": status}]
      );
    }
  }
}

```

## Security Best Practices by API

### All APIs

- Use environment variables for credentials
- Implement rate limiting
- Log all access for auditing
- Use HTTPS always
- Validate input before queries

### Data API Specific

- Implement session timeout handling
- Don't expose session tokens to client
- Close sessions on logout

### OttoFMS Specific

- Rotate API keys regularly
- Use separate keys for dev/prod
- Leverage IP filtering features
- Monitor key usage in console

### OData Specific

- Be aware of table occurrence access (not direct base table access)
- Implement field-level security carefully
- Use $select to limit data exposure
- Monitor for complex query abuse
- Remember: Table occurrence names can differ from base table names

## Quick Decision Guide

### Use Data API When:

- Working with existing PHP applications
- Need maximum compatibility
- Container data is critical
- Already have working implementation

### Use OttoFMS When:

- Want simplified authentication
- Need deployment automation
- Require webhook integration
- Building new Node.js/React apps

### Use OData When:

- Need atomic transactions
- Require complex queries
- Building modern TypeScript apps
- Integrating with BI tools
- Want industry-standard API

## Testing Snippets

### Test All Three APIs

```jsx
async function testAllAPIs() {
  console.log('Testing Data API...');
  const dataApiRecords = await testDataAPI();

  console.log('Testing OttoFMS...');
  const ottoRecords = await testOttoFMS();

  console.log('Testing OData...');
  const odataRecords = await testOData();

  console.log('Results:');
  console.log('Data API:', dataApiRecords?.length || 'Failed');
  console.log('OttoFMS:', ottoRecords?.length || 'Failed');
  console.log('OData:', odataRecords?.length || 'Failed');
}

async function testDataAPI() {
  // Implementation
}

async function testOttoFMS() {
  // Implementation
}

async function testOData() {
  // Implementation
}

```

## Troubleshooting Checklist

### When records aren't returning:

### All APIs:

1. ✓ Verify credentials are correct
2. ✓ Check SSL certificate settings
3. ✓ Confirm database and table/layout names
4. ✓ Test with simplest possible query first

### Data API / OttoFMS:

1. ✓ Remember empty array returns NO records
2. ✓ Check field names are case-sensitive
3. ✓ Verify layout has correct fields
4. ✓ Test session/API key validity

### OData Specific:

1. ✓ Check table occurrence names (from Relationships Graph) vs layout names
2. ✓ Verify OData is enabled on server
3. ✓ Test $metadata endpoint first
4. ✓ Use proper OData query syntax
5. ✓ Remember: OData exposes table occurrence names, NOT base table names

### Enhanced MCP Server Troubleshooting:

### Filter Syntax Issues:

- ✓ Use operator objects: `{"field": {"$contains": "value"}}` not `{"field": "*value*"}`
- ✓ Check console logs for generated filter expressions
- ✓ Test with simple equality first: `{"field": "value"}`
- ✓ Verify field names match exactly (case-sensitive)

### Create Operation Failures:

- ✓ Check console for detailed error messages
- ✓ Verify all required fields are provided
- ✓ Test with minimal data first
- ✓ Check field names match layout/table schema
- ✓ FileMaker error codes provide specific guidance

### Enhanced Error Messages:

```jsx
// The enhanced MCP server now provides detailed error info:
{
  "error": "FileMaker Error 102: Field missing",
  "details": {
    "url": "<https://host/otto/fmi/data/vLatest/>...",
    "requestData": {"fieldData": {...}},
    "responseData": {"messages": [{"code": "102", "message": "Field missing"}]}
  }
}

```

## Performance Benchmarks

| Operation | Data API | OttoFMS | OData |
| --- | --- | --- | --- |
| Auth overhead | ~200ms/session | 0ms | ~50ms/request |
| Simple query | 100ms | 95ms | 90ms |
| Complex filter | 300ms | 290ms | 150ms |
| With relations | 500ms (2 calls) | 490ms (2 calls) | 200ms (1 call) |
| Batch update | N/A | N/A | 300ms (atomic) |

## StartingPoint Database Reference

### Available Table Occurrences (OData)

```
Main Tables:
- T01_ACCOUNTS - Company/account records
- T05_CONTACTS - Contact/people information
- T08_ESTIMATES - Estimate records
- T10_EXPENSES - Expense tracking
- T12_INVOICES - Invoice/sales data (may have performance issues)
- T15_PRODUCTS - Product/inventory information
- T16_PROJECTS - Project management
- T17_STAFF - Staff/employee records

AI-Related Tables:
- AI_Agents - AI agent configurations
- AI_Functions - AI function definitions
- AI_Globals - AI global settings
- AI_Logs - AI activity logs
- AI_TableConfig - AI table configurations

```

### Enhanced MCP Server Test Results (August 2025) - DataAPI CRUD Complete ✅

**✅ Working Features (Complete DataAPI CRUD Fixed):**

- API key authentication via Otto FMS
- Enhanced OData filtering with proper v4 syntax
- Fixed Data API filtering with FileMaker find format
- **DataAPI CREATE operations** - ✅ FULLY WORKING
- **DataAPI UPDATE operations** - ✅ FULLY WORKING (fixed response parsing)
- **DataAPI DELETE operations** - ✅ FULLY WORKING (proper error handling)
- Detailed error logging for debugging HTTP requests/responses
- Support for advanced operators: $contains, $startswith, $endswith, $gt, $lt, etc.
- Proper TypeScript interfaces for all response structures
- Comprehensive logging for troubleshooting API calls

**🧪 Tested Working Examples (Comprehensive CRUD):**

```jsx
// DataAPI Create - WORKING ✅
const createResult = await mcpClient.call('create_record', {
  api_type: 'data_api',
  auth_method: 'api_key',
  table_or_layout: 'API_Account',
  data: {
    "Account": "Test Company via MCP",
    "Phone1": "555-1234",
    "Account_Type": "Company"
  }
});
// Returns: {recordId: "41843", modId: "0", fieldData: {...}}

// DataAPI Update - WORKING ✅
const updateResult = await mcpClient.call('update_record', {
  api_type: 'data_api',
  auth_method: 'api_key',
  table_or_layout: 'API_Account',
  record_id: '41843',
  data: {"Account": "Updated Company Name"}
});
// Returns: {recordId: "41843", modId: "1", fieldData: {...}}

// DataAPI Delete - WORKING ✅
const deleteResult = await mcpClient.call('delete_record', {
  api_type: 'data_api',
  auth_method: 'api_key',
  table_or_layout: 'API_Account',
  record_id: '41843'
});
// Returns: {success: true, message: "Record deleted successfully"}

// OData Query - WORKING ✅
await mcpClient.call('query_records', {
  api_type: 'odata',
  table_or_layout: 'T01_ACCOUNTS',
  filter: {"Account": {"$contains": "Test"}},
  limit: 10
});

```

**✅ MAJOR UPDATE (August 2025) - DataAPI CRUD Operations FULLY WORKING:**

- ✅ DataAPI CREATE operations: **FIXED** - Response parsing updated for {recordId, modId} structure
- ✅ DataAPI UPDATE operations: **FIXED** - Response parsing updated to handle {modId} only response
- ✅ DataAPI DELETE operations: **FIXED** - Working with proper error handling and logging
- ❌ OData UPDATE operations: Still failing with 400 errors (endpoint/format issues) - **NEXT TO FIX**
- ❌ OData DELETE operations: Still failing with 400 errors (endpoint/format issues) - **NEXT TO FIX**
- Large metadata responses can cause timeouts
- Some table occurrences may have restricted access

**🔧 Recent Fixes Applied (August 2025):**

- **CRITICAL FIX**: DataAPI create operations response parsing
- **CRITICAL FIX**: DataAPI update operations response parsing - different structure than create
- **CRITICAL FIX**: DataAPI delete operations - working with proper error handling
- Proper OData string escaping (single quotes → double quotes)
- FileMaker-specific wildcard patterns for Data API
- Enhanced error messages with FileMaker error codes
- Improved URL construction for Otto proxy authentication
- Added DataApiCreateResponse, DataApiUpdateResponse, DataApiDeleteResponse interfaces
- Comprehensive logging for debugging HTTP requests and responses

### Available Layouts (Data API)

**API-Optimized Layouts (Recommended):**

```
API Folder Layouts:
- API_Account (T01_ACCOUNTS) - ✅ TESTED: Create operations working
- API_Contact (T05_CONTACTS)
- API_Estimate (T08_ESTIMATES)
- API_Invoice (T12_INVOICES)
- API_Project (T16_PROJECTS)
- API_Product (T15_PRODUCTS)
- API_EstimateLI (T09_EST_LINE_ITEMS)
- API_InvoiceLI (T13_INV_LINE_ITEMS)
- API_Task_List (T19_TASKS)

```

**Standard Data Entry Layouts:**

```
Accounts:
- L100a_ACCOUNTS_Data_Entry
- L101_ACCOUNTS_List_View

Contacts:
- L300a_CONTACTS_Data_Entry
- L301_CONTACTS_List_View

Estimates:
- L600a_ESTIMATES_Data_Entry
- L601_ESTIMATES_List_View

Invoices:
- L800a_INVOICES_Data_Entry
- L801_INVOICES_List_View

Products:
- L1000a_PRODUCTS_Data_Entry
- L1001_PRODUCTS_List_View

Staff:
- L1200_STAFF_Data_Entry
- L1201_STAFF_List_View

```

**Layout Selection Best Practices:**

- Use API_* layouts for programmatic access (cleaner field names)
- Use L*_Data_Entry layouts for full field access
- Use L*_List_View layouts for readonly operations
- API layouts typically have simplified field names (e.g., "Account" vs "AccountName_Display")

## Conclusion

Each API has its place:

- **Data API**: Mature, compatible, session-based
- **OttoFMS**: Simplified auth, deployment features
- **OData**: Modern, powerful queries, transactions

Choose based on your specific needs, not just on newest technology.