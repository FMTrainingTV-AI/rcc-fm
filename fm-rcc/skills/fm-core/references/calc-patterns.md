# FileMaker Calculation Patterns Reference

## Table of Contents
1. JSON Building & Parsing
2. Text Formatting & Styling
3. Date & Time Handling
4. ExecuteSQL Patterns
5. Conditional Logic
6. List & Array Processing
7. Error-Safe Patterns

---

## 1. JSON Building & Parsing

### Build a JSON object from fields
```
JSONSetElement ( "{}" ;
  [ "name" ; Table::Name ; JSONString ] ;
  [ "email" ; Table::Email ; JSONString ] ;
  [ "age" ; Table::Age ; JSONNumber ] ;
  [ "active" ; Table::IsActive ; JSONBoolean ]
)
```

### Build a JSON object incrementally
```
Let ( [
  _json = "{}" ;
  _json = JSONSetElement ( _json ; "key1" ; "value1" ; JSONString ) ;
  _json = JSONSetElement ( _json ; "key2" ; 42 ; JSONNumber )
] ;
  _json
)
```

### Build a JSON array from a return-delimited list
```
Let ( [
  _list = "apple¶banana¶cherry" ;
  _count = ValueCount ( _list ) ;
  _json = "[]" ;
  _i = 1
] ;
  // Note: FileMaker doesn't have loops in calcs — use recursive custom function
  // or build in a script with a Loop step
  _json
)
```
**In scripts**, use a Loop:
```
Set Variable [$json ; "[]"]
Set Variable [$i ; 1]
Loop
  Exit Loop If [$i > ValueCount ( $list )]
  Set Variable [$json ; JSONSetElement ( $json ; $i - 1 ; GetValue ( $list ; $i ) ; JSONString )]
  Set Variable [$i ; $i + 1]
End Loop
```

### Validate JSON before parsing
```
Let ( [
  _json = Table::JsonField ;
  _valid = not IsEmpty ( _json ) and Left ( JSONFormatElements ( _json ) ; 1 ) <> "?"
] ;
  Case ( not _valid ; "" ;
    JSONGetElement ( _json ; "someKey" )
  )
)
```

### Safely get a value with fallback
```
Let ( [
  _val = JSONGetElement ( _json ; "key" )
] ;
  Case ( IsEmpty ( _val ) or _val = "null" ; "Default value" ; _val )
)
```

---

## 2. Text Formatting & Styling

### Bold label with value
```
TextStyleAdd ( "Label: " ; Bold ) & fieldValue
```

### Multi-section formatted display
```
TextStyleAdd ( "Section Title" ; Bold ) & "¶" &
contentText & "¶¶" &
TextStyleAdd ( "Next Section" ; Bold ) & "¶" &
moreContent
```

### Bullet list from return-delimited text
```
Case ( IsEmpty ( _items ) ;
  TextStyleAdd ( "None" ; Italic ) ;
  "• " & Substitute ( _items ; "¶" ; "¶• " )
)
```

### Colored text
```
TextColor ( "Warning: " ; RGB ( 255 ; 0 ; 0 ) ) & warningMessage
```

### Combined styling
```
TextStyleAdd ( TextColor ( "Important" ; RGB ( 200 ; 0 ; 0 ) ) ; Bold + Italic )
```

---

## 3. Date & Time Handling

### Format date as YYYY-MM-DD (API-safe)
```
Let ( [
  _d = Get ( CurrentDate )
] ;
  Year ( _d ) & "-" &
  Right ( "0" & Month ( _d ) ; 2 ) & "-" &
  Right ( "0" & Day ( _d ) ; 2 )
)
```

### Format timestamp as ISO 8601
```
Let ( [
  _ts = Get ( CurrentTimestamp ) ;
  _d = GetAsDate ( _ts ) ;
  _t = GetAsTime ( _ts )
] ;
  Year ( _d ) & "-" &
  Right ( "0" & Month ( _d ) ; 2 ) & "-" &
  Right ( "0" & Day ( _d ) ; 2 ) & "T" &
  Right ( "0" & Hour ( _t ) ; 2 ) & ":" &
  Right ( "0" & Minute ( _t ) ; 2 ) & ":" &
  Right ( "0" & Seconds ( _t ) ; 2 )
)
```

### Add days/months to a date
```
Get ( CurrentDate ) + 14                          // 14 days from now
Date ( Month ( _d ) + 6 ; Day ( _d ) ; Year ( _d ) )  // 6 months from now
```

### Parse a date string (YYYY-MM-DD)
```
Let ( [
  _str = "2026-04-13" ;
  _y = Left ( _str ; 4 ) ;
  _m = Middle ( _str ; 6 ; 2 ) ;
  _d = Right ( _str ; 2 )
] ;
  Date ( _m ; _d ; _y )
)
```

---

## 4. ExecuteSQL Patterns

**Important:** ExecuteSQL queries the relationship graph, so you must use **table occurrence (TO) names**, not base table names. If the base table is `DataAPI` but the TO on the graph is `zDataAPI`, use `FROM zDataAPI`.

### Basic SELECT with parameter
```
ExecuteSQL ( "SELECT Email FROM Contacts WHERE ContactID = ?" ; "" ; "" ; $contactID )
```

### Multiple columns with custom separator
```
ExecuteSQL ( "SELECT FirstName, LastName FROM Contacts WHERE Active = 1" ; " | " ; "¶" )
```
Returns: `John | Smith¶Jane | Doe`

### COUNT / aggregate
```
ExecuteSQL ( "SELECT COUNT(*) FROM Invoices WHERE Status = ?" ; "" ; "" ; "unpaid" )
```

### JOIN across tables
```
ExecuteSQL (
  "SELECT c.Name, i.Total FROM Contacts c JOIN Invoices i ON c.ContactID = i.ContactID WHERE i.Total > ?" ;
  " | " ; "¶" ; 1000
)
```

### Date comparison in SQL
```
ExecuteSQL (
  "SELECT Name FROM Events WHERE EventDate > DATE '2026-01-01'" ;
  "" ; ""
)
```

### Error checking
```
Let ( [
  _result = ExecuteSQL ( "SELECT Name FROM SomeTable" ; "" ; "" )
] ;
  Case ( Left ( _result ; 1 ) = "?" ; "SQL Error" ; _result )
)
```

### Trim whitespace from results
ExecuteSQL can return trailing whitespace. Wrap with `Trim()` when the result is a single value:
```
Trim ( ExecuteSQL ( "SELECT APIKey FROM zDataAPI WHERE DataAPIID = ?" ; "" ; "" ; 1 ) )
```

---

## 5. Conditional Logic

### Nested Case with multiple conditions
```
Case (
  score >= 90 ; "A" ;
  score >= 80 ; "B" ;
  score >= 70 ; "C" ;
  score >= 60 ; "D" ;
  "F"
)
```

### Choose (index-based)
```
Choose ( dayOfWeek ;
  "Sunday" ; "Monday" ; "Tuesday" ; "Wednesday" ; "Thursday" ; "Friday" ; "Saturday"
)
```

### Conditional with empty/null handling
```
Case (
  IsEmpty ( field ) ; "Not provided" ;
  field = "null" ; "Not provided" ;
  field
)
```

---

## 6. List & Array Processing

### ValueCount and GetValue
```
Let ( [
  _list = "apple¶banana¶cherry" ;
  _count = ValueCount ( _list ) ;
  _second = GetValue ( _list ; 2 )       // "banana"
] ;
  _count & " items, second is: " & _second
)
```

### Filter a list (in a script Loop)
```
Set Variable [$filtered ; ""]
Set Variable [$i ; 1]
Loop
  Exit Loop If [$i > ValueCount ( $source )]
  Set Variable [$item ; GetValue ( $source ; $i )]
  If [PatternCount ( $item ; "search" ) > 0]
    Set Variable [$filtered ; List ( $filtered ; $item )]
  End If
  Set Variable [$i ; $i + 1]
End Loop
```

### Deduplicate a list (via UniqueValues in FM 18+)
```
UniqueValues ( $list )
```

### Sort a list (FM 18+)
```
SortValues ( $list ; 1 )    // 1 = ascending, 2 = descending
```

---

## 7. Error-Safe Patterns

### Safe field reference with GetField
```
GetField ( "TableName::FieldName" )
```
Useful when field name is dynamic / stored in a variable.

### Guarded division
```
Case ( denominator = 0 ; 0 ; numerator / denominator )
```

### Safe JSON extraction with fallback
```
Let ( [
  _raw = JSONGetElement ( _json ; "key" )
] ;
  Case (
    IsEmpty ( _raw ) ; "N/A" ;
    _raw = "null" ; "N/A" ;
    _raw
  )
)
```

### IsValid check before using a field
```
Case ( IsValid ( Table::Field ) ; Table::Field ; "Invalid" )
```
