# FileMaker DDR XML Structure Reference

## Overview

The FileMaker Database Design Report (DDR) is an XML export of a database's entire structure — tables, fields, scripts, layouts, relationships, and all metadata. It does not contain record data, only the design.

## Export Types

### DDR XML (File > Manage > Database Design Report)
- Available in all FileMaker versions (12+)
- Exports one XML file per database in the solution, plus a `Summary.xml`
- Root element: `<FMPReport>`
- Most complete representation of database design

### Save a Copy as XML (File > Save a Copy as > XML)
- Available in FileMaker 19.6+
- Root element: `<FMSaveAsXML>` (clipboard/snippet-style `AddAction` structure)
- Different element structure but similar content
- Used by fm-xml-export-exploder
- **FileMaker 2026 (`Source="26.x"`) splits this into a folder of per-catalog files** (`split_catalogs="True"`) and adds resolved cross-references + a `DDR_INFO` text store. This is now the richest export for agentic use — see [FileMaker 2026 Split-Catalog Format](#filemaker-2026-split-catalog-format-fmsaveasxml) below. Parsed by `scripts/fmsaveasxml.py`.

## Encoding

**Classic `<FMPReport>` DDR files are UTF-16 LE encoded** (with BOM), not UTF-8. lxml auto-detects this from the BOM when you use `etree.parse()` without specifying an encoding. **FM 2026 `<FMSaveAsXML>` split-catalog files are UTF-8** (per their XML declaration).

## FileMaker 2026 Split-Catalog Format (`<FMSaveAsXML>`)

*Confirmed from a real FM 2026 export (`Source="26.0.1"`, `version="2.3.0.0"`), 2026-06-29.*

FileMaker 2026's "Save a Copy as XML" exports a **folder per database**, one XML file per catalog, instead of a single document. `Summary.xml` is still an `<FMPReport type="Summary">` but points at the folder via an `<XML path>` child rather than a `link` attribute:

```xml
<FMPReport type="Summary" version="2.3.0.0" membercount="1">
  <File name="MyFile.fmp12" path="10.0.7.20">
    <XML path="/abs/path/to/MyFile/"></XML>   <!-- folder of catalog files -->
  </File>
</FMPReport>
```

Each catalog file (`MyFile_FieldCatalog.xml`, `MyFile_ScriptCatalog.xml`, …) has the same two-branch shape:

```xml
<FMSaveAsXML version="2.3.0.0" Source="26.0.1" File="MyFile.fmp12"
             Has_DDR_INFO="True" split_catalogs="True">
  <Structure><AddAction><XxxCatalog>…</XxxCatalog></AddAction></Structure>
  <DDR_INFO>…</DDR_INFO>
</FMSaveAsXML>
```

**`Structure/AddAction/<Catalog>`** — the definitions. Richer than classic DDR:
- Per-object `<UUID modifications=… userName=… accountName=… timestamp=…>` change-tracking metadata.
- Calculations and references are **pre-resolved in place**: `<TableOccurrenceReference id name UUID/>`, `<FieldReference id name UUID>`, `<ScriptReference id name UUID/>`, plus the raw calc `<Text>`. No need to parse the relationship graph to know what a calc depends on.

**`DDR_INFO`** — a content-addressable text store. Calc/step text is split into hashed `<Chunk>`s grouped under `<ChunkList hash=…>` and under `_<UUID>[_n]`-named elements. A `<DDRREF kind="StepText|ChunkList" hash=…>_<UUID>…</DDRREF>` in the structure references a store entry **by its text content** (the `_<UUID>` key), *not* by the hash. The human-readable one-line step text (`Set Variable [ $x ; Value: … ]`) lives only here, under `kind="StepText"`.

### Per-catalog quirks (FM 2026)

| Catalog file | Holds | Notes |
|---|---|---|
| `BaseTableCatalog` | `<BaseTable id name comment>` | table list + id→name |
| `FieldCatalog` | `<FieldsForTables><FieldCatalog>…<Field fieldtype datatype>` | per-table blocks have **no name/id** — map to tables **positionally** (document order matches `BaseTableCatalog`) |
| `ScriptCatalog` | `<ScriptCatalog>` (Group/Script hierarchy) **and** `<StepsForScripts>` (`<Script><ScriptReference/><ObjectList><Step>`) | two sections; join by `id`. Steps carry typed `<ParameterValues>` + `DDRREF kind="StepText"` |
| `LayoutCatalog` | flat `<Layout id name [isFolder] [width]>` | folders are `isFolder="True"` markers in the flat list, not nesting |
| Accounts / CustomFunctions / PrivilegeSets / ExtendedPrivileges | items inside an `<ObjectList>` wrapper | other catalogs list items directly under the catalog |
| field type attr | `fieldtype` (lowercase), `datatype` | classic DDR used `fieldType`/`type` |

`scripts/fmsaveasxml.py` normalizes all of this into the standard `parsed/<db>/<type>/` layout (writing `<StepText>` back into each step), so `summary.py` / `refs.py` / `orphans.py` / `search.py` / `compare.py` work unchanged. Run `python3 scripts/test_fmsaveasxml.py` to verify against the fixture.

## DDR XML Root Structure

### FM 22 (confirmed from real DDR, 2026-02-13)

```xml
<?xml version="1.0"?>
<FMPReport link="Summary.xml" creationTime="..." creationDate="2026-02-13" type="Report" version="22.0.2">
  <File name="Production.fmp12" path="SAURFMPRO01">
    <BaseTableCatalog>...</BaseTableCatalog>
    <BaseDirectoryCatalog>...</BaseDirectoryCatalog>
    <RelationshipGraph>
      <TableList>...</TableList>           <!-- Table Occurrences live here -->
      <RelationshipList>...</RelationshipList>  <!-- Relationships live here -->
    </RelationshipGraph>
    <LayoutCatalog>...</LayoutCatalog>
    <ValueListCatalog>...</ValueListCatalog>
    <ScriptCatalog>...</ScriptCatalog>
    <AccountCatalog>...</AccountCatalog>
    <PrivilegesCatalog>...</PrivilegesCatalog>    <!-- Note: not PrivilegeSetCatalog -->
    <ExtendedPrivilegeCatalog>...</ExtendedPrivilegeCatalog>
    <AuthFileCatalog>...</AuthFileCatalog>         <!-- File Access authorizations -->
    <CustomFunctionCatalog>...</CustomFunctionCatalog>
    <ExternalDataSourcesCatalog>...</ExternalDataSourcesCatalog>  <!-- Note the 's' -->
    <CustomMenuSetCatalog>...</CustomMenuSetCatalog>
    <CustomMenuCatalog>...</CustomMenuCatalog>
    <Options>...</Options>
    <ThemeCatalog>...</ThemeCatalog>
```

### Older FM versions (12-19, from documentation — not yet confirmed)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FMPReport link="Summary.xml" type="Report" version="12.0v1">
  <File name="DatabaseName" id="1">
    <BaseTableCatalog>...</BaseTableCatalog>
    <TableOccurrenceCatalog>...</TableOccurrenceCatalog>
    <RelationshipCatalog>...</RelationshipCatalog>
    <ScriptCatalog>...</ScriptCatalog>
    <LayoutCatalog>...</LayoutCatalog>
    <ValueListCatalog>...</ValueListCatalog>
    <CustomFunctionCatalog>...</CustomFunctionCatalog>
    <CustomMenuCatalog>...</CustomMenuCatalog>
    <CustomMenuSetCatalog>...</CustomMenuSetCatalog>
    <AccountCatalog>...</AccountCatalog>
    <PrivilegeSetCatalog>...</PrivilegeSetCatalog>
    <ExtendedPrivilegeCatalog>...</ExtendedPrivilegeCatalog>
    <ExternalDataSourceCatalog>...</ExternalDataSourceCatalog>
    <ThemeCatalog>...</ThemeCatalog>
  </File>
</FMPReport>
```

## Key Elements

### External Data Sources

```xml
<ExternalDataSourceCatalog>
  <ExternalDataSource id="1" name="OtherDatabase">
    <PathList>
      <Path>file:OtherDatabase</Path>
      <Path>fmnet:/server.example.com/OtherDatabase</Path>
    </PathList>
  </ExternalDataSource>
</ExternalDataSourceCatalog>
```

### Table Occurrences

```xml
<TableOccurrenceCatalog>
  <TableOccurrence id="1065089" name="Orders" baseTable="Orders" baseTableId="1065089">
    <!-- Local table reference -->
  </TableOccurrence>
  <TableOccurrence id="1065090" name="Invoices_EXTERNAL" baseTable="Invoices"
                   baseTableId="129" baseTableSourceType="File">
    <FileReference id="1" name="OtherDatabase"/>
    <!-- External table reference — key for tracing cross-file dependencies -->
  </TableOccurrence>
</TableOccurrenceCatalog>
```

**Key attributes:**
- `baseTable` — The actual table name
- `baseTableSourceType` — "File" means it's from an external data source
- `FileReference` child — Points to the external data source

### Base Tables and Fields

```xml
<BaseTableCatalog>
  <BaseTable id="1065089" name="Orders">
    <FieldCatalog>
      <Field id="1" name="ID" fieldType="Normal" dataType="Number">
        <AutoEnter type="Serial" allowEditing="False"/>
        <Storage global="False" index="All"/>
      </Field>
      <Field id="5" name="Total" fieldType="Calculated" dataType="Number">
        <Calculation table="Orders">
          <![CDATA[SubTotal + Tax + Shipping]]>
        </Calculation>
        <Storage global="False" index="None"/>
      </Field>
      <Field id="10" name="CustomerName" fieldType="Calculated" dataType="Text">
        <Calculation table="Orders">
          <![CDATA[Customers_ORDERS::FirstName & " " & Customers_ORDERS::LastName]]>
        </Calculation>
      </Field>
      <Field id="20" name="Summary_Total" fieldType="Summary">
        <SummaryInfo operation="Total" field="Total"/>
      </Field>
    </FieldCatalog>
  </BaseTable>
</BaseTableCatalog>
```

**Field types:** `Normal`, `Calculated`, `Summary`, `Global`
**Data types:** `Text`, `Number`, `Date`, `Time`, `Timestamp`, `Container`

### Relationships

```xml
<RelationshipCatalog>
  <Relationship id="1">
    <LeftTable id="1065089" name="Orders"/>
    <RightTable id="1065090" name="Invoices_EXTERNAL"/>
    <JoinPredicateList>
      <JoinPredicate type="equal">
        <LeftField id="1" name="OrderID" table="Orders"/>
        <RightField id="5" name="OrderID" table="Invoices_EXTERNAL"/>
      </JoinPredicate>
    </JoinPredicateList>
    <Options cascadeDelete="False" cascadeCreate="False"/>
  </Relationship>
</RelationshipCatalog>
```

### Scripts

```xml
<ScriptCatalog>
  <Group name="Billing">
    <Script id="100" name="Create Invoice" includeInMenu="True">
      <StepList>
        <Step id="1" name="Go to Layout" enable="True">
          <Layout id="50" name="Invoice Detail"/>
        </Step>
        <Step id="2" name="New Record/Request" enable="True"/>
        <Step id="3" name="Set Field" enable="True">
          <Field table="Invoices_EXTERNAL" id="10" name="Date"/>
          <Calculation>
            <![CDATA[Get(CurrentDate)]]>
          </Calculation>
        </Step>
        <Step id="4" name="Perform Script" enable="True">
          <Script id="101" name="Calculate Totals"/>
          <Parameter>
            <Calculation><![CDATA[Orders::ID]]></Calculation>
          </Parameter>
        </Step>
        <Step id="5" name="Set Field By Name" enable="True">
          <!-- Dynamic field reference — cannot be statically traced -->
          <Calculation>
            <![CDATA["Orders::" & $fieldName]]>
          </Calculation>
        </Step>
      </StepList>
    </Script>
  </Group>
  <Script id="200" name="Standalone Script">
    <!-- Script not in a group -->
  </Script>
</ScriptCatalog>
```

**Important script step types for reference tracing:**
- `Set Field` — references a specific TO::Field
- `Set Field By Name` — dynamic, calculated field reference (hard to trace statically)
- `Go to Layout` — references a layout
- `Go to Related Record` — references a TO and optionally a layout
- `Perform Script` — references another script
- `Perform Script on Server` — references another script
- `Set Variable` — may contain TO::Field in calculation
- `If/Else If` — conditions may reference TO::Field
- `Loop/Exit Loop If` — conditions may reference TO::Field
- `Insert from URL` — may reference fields for URL or target
- `Execute SQL` — SQL text may reference table/field names

### Layouts

```xml
<LayoutCatalog>
  <Group name="Data Entry">
    <Layout id="50" name="Invoice Detail"
            baseTable="Invoices_EXTERNAL" baseTableId="1065090">
      <ObjectList>
        <Object type="Field" name="">
          <FieldObj table="Invoices_EXTERNAL" id="10" name="Date"/>
          <Bounds top="100" left="200" bottom="120" right="400"/>
        </Object>
        <Object type="Field" name="">
          <FieldObj table="Invoices_EXTERNAL" id="15" name="Total"/>
        </Object>
        <Object type="Text" name="">
          <TextObj>
            <Paragraph>
              <Text>Invoice: <<Invoices_EXTERNAL::InvoiceNumber>></Text>
            </Paragraph>
          </TextObj>
        </Object>
        <Object type="Button" name="Print">
          <Script id="150" name="Print Invoice"/>
        </Object>
      </ObjectList>
      <ScriptTriggerList>
        <ScriptTrigger event="OnRecordLoad">
          <Script id="180" name="Load Invoice Data"/>
        </ScriptTrigger>
      </ScriptTriggerList>
    </Layout>
  </Group>
</LayoutCatalog>
```

**Layout object types:** `Field`, `Text`, `Button`, `Portal`, `Tab Control`, `Slide Panel`, `Web Viewer`, `Chart`, `ButtonBar`

### Value Lists

```xml
<ValueListCatalog>
  <ValueList id="1" name="Status Values">
    <CustomValues>
      <Value>Active</Value>
      <Value>Inactive</Value>
      <Value>Pending</Value>
    </CustomValues>
  </ValueList>
  <ValueList id="2" name="Customer Names">
    <Field table="Customers" id="5" name="FullName"/>
    <SecondField table="Customers" id="1" name="ID"/>
    <SortBy value="FirstField"/>
  </ValueList>
</ValueListCatalog>
```

### Custom Functions

```xml
<CustomFunctionCatalog>
  <CustomFunction id="1" name="TrimAll" parameters="text">
    <Calculation>
      <![CDATA[
        Substitute(
          Trim(text);
          ["  "; " "]
        )
      ]]>
    </Calculation>
  </CustomFunction>
</CustomFunctionCatalog>
```

### Accounts and Privilege Sets

```xml
<AccountCatalog>
  <Account id="1" name="Admin" type="FileMaker" privilegeSet="[Full Access]" status="Active"/>
  <Account id="2" name="DataEntry" type="FileMaker" privilegeSet="Data Entry Only" status="Active"/>
</AccountCatalog>

<PrivilegeSetCatalog>
  <PrivilegeSet id="1" name="Data Entry Only">
    <RecordAccessPrivileges>
      <TablePrivilege table="Orders" create="Yes" edit="Limited" delete="No" view="Yes">
        <CalculatedPrivilege type="edit">
          <![CDATA[Orders::Status = "Draft"]]>
        </CalculatedPrivilege>
      </TablePrivilege>
    </RecordAccessPrivileges>
  </PrivilegeSet>
</PrivilegeSetCatalog>
```

## Version Differences

### Catalog Name Changes (CRITICAL for parsing)

| Object | FM 12-19 (documented) | FM 22 (confirmed) |
|---|---|---|
| Table Occurrences | `TableOccurrenceCatalog` | `RelationshipGraph` > `TableList` |
| Relationships | `RelationshipCatalog` | `RelationshipGraph` > `RelationshipList` |
| External Data Sources | `ExternalDataSourceCatalog` | `ExternalDataSourcesCatalog` (note 's') |
| Privilege Sets | `PrivilegeSetCatalog` | `PrivilegesCatalog` |
| File Access | (not present) | `AuthFileCatalog` |
| File/DB directory | (not present) | `BaseDirectoryCatalog` |

### Other Changes

| Element | FM 12-18 | FM 19+ | FM 22 (confirmed) |
|---|---|---|---|
| Encoding | UTF-16 LE | UTF-16 LE | UTF-16 LE |
| Themes | Basic | Full ThemeCatalog | Full ThemeCatalog |
| Add-ons | N/A | N/A | Not confirmed yet |
| Script triggers | Limited | Full list | Full list |
| Layout objects | Basic types | More object types | Card windows, popovers |
| Custom menus | Basic | Full | Full with separators |

> **Parser strategy:** Check for both old and new catalog names to support multiple FM versions. For TOs, check `TableOccurrenceCatalog` first, then fall back to `RelationshipGraph/TableList`.

## Common Patterns for Reference Tracing

### Finding all references to an external file

1. Match name in `ExternalDataSourcesCatalog` (FM 22) or `ExternalDataSourceCatalog` (older)
2. Find TOs where `FileReference` name matches — check `RelationshipGraph/TableList` (FM 22) or `TableOccurrenceCatalog` (older)
3. For each TO name, search:
   - `Calculation` CDATA for `TOName::`
   - `Step` elements for `Field table="TOName"`
   - `FieldObj table="TOName"` in layouts
   - `ValueList` Field elements with `table="TOName"`
   - `JoinPredicate` fields with matching TO names
   - `ScriptTrigger` → `Script` for related scripts
   - Merge fields in text: `<<TOName::FieldName>>`

### Finding orphaned objects

1. Collect all defined names (TOs, fields, scripts, layouts)
2. Scan all text content for references to those names
3. Objects with zero references are orphan candidates
4. Filter false positives (entry-point scripts, default layouts, relationship keys)
