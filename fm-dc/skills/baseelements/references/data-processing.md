# BE Data processing recipes — JSON (jq), XML/XPath/XSLT, regex, lists, vectors

## jq over JSON — `BE_JSON_jq`

`jq` is a full JSON query language — vastly more capable than `JSONGetElement` for filtering, mapping,
selecting, and aggregating. Use it when a query would need many nested `JSONGetElement`/`JSONListValues`
calls or a loop.

```
# pull a field from every array element
BE_JSON_jq ( $json ; ".productTypes[].name" )

# filter, sort, aggregate — "r" = raw output (unquoted scalar instead of JSON-quoted)
BE_JSON_jq ( $json ; "[ .prices[] | select(.quantity == 1) ] | max_by(.price) | .price" ; "r" )

# reach deep into a nested structure
BE_JSON_jq ( $json ; ".data.products.edges[].node.category.name" ; "r" )
```

Signature: `BE_JSON_jq ( json ; filter ; { options } )`. `"r"` = raw string output.
`BE_JSON_ArraySize ( json ; { path } )` returns the element count of a JSON array.

Check `BE_GetLastError` after — a bad filter or malformed JSON reports there.

## XPath over XML — `BE_XPath` / `BE_XPathAll`

```
# first matching node/attribute (with a namespace map: "prefix=uri¶prefix2=uri2")
BE_XPath ( $xml ; "/abc:checkUserResponse/abc:result/@type" ; "abc=http://xml.example.com/2009" )

# all matching nodes (returns a ¶-separated list)
BE_XPathAll ( $xml ; "//book/title" )
```

- `BE_XPath ( xmlText ; xpathText ; { namespaceList ; asText } )` — first match.
- `BE_XPathAll ( xmlText ; xpathText ; { namespaceList } )` — every match.
- Namespaces: pass `"prefix=uri"` entries, ¶-separated, and use those prefixes in the XPath.

## XSLT transforms

```
# transform XML text → result text, all in memory
Set Variable [ $out ; BE_XSLT_ApplyInMemory ( $xmlText ; $xsltText ) ]

# transform an XML file on disk → output file (paths are POSIX)
Set Variable [ $r ; BE_XSLTApply ( $xmlFilePath ; $xsltText ; $outputFilePath ) ]
```

## XML utilities

```
BE_XMLParse ( $pathOrXMLText )                       // is it well-formed? (validity check)
BE_XMLValidate ( $xmlText ; $xsdSchemaText )         // validate against an XSD
BE_XMLTidy ( $xml )                                  // pretty-print / reformat
BE_XML_Canonical ( $xml )                            // canonical form, for reliable comparison
BE_XMLStripInvalidCharacters ( $path ; $resultPath ) // strip illegal XML chars from a file
BE_XMLStripNodes ( $inPath ; $outPath ; $nodeNames ) // remove named nodes from an XML file
```

## Regex — `BE_RegularExpression`

PCRE (Perl-compatible). Match (returns first match) or replace (pass `replaceString`):

```
BE_RegularExpression ( "abc 123 def" ; "[0-9]+" )            // = "123"  (first match)
BE_RegularExpression ( $text ; "\\s+" ; "g" ; " " )          // replace: collapse whitespace (g = global)
```

Signature: `( text ; expression ; { options ; replaceString } )`. Common options: `i`
(case-insensitive), `g` (global), `m` (multiline), `v` (return a value-per-line list of matches over a
¶-list input). Escape backslashes in the calc (`\\d`, `\\s`, `\\.`).

`BE_TextExtractWords ( text ; { wordPrefix } )` — list the words in text; with a prefix char, only words
starting with it (e.g. `"@"` for mentions, `"#"` for tags).

## Value-list helpers (FileMaker ¶-separated lists)

```
BE_ValuesUnique ( $list )                       // de-duplicate
BE_ValuesSort ( $list ; True )                  // sort ascending (False = descending)
BE_ValuesTrim ( $list )                         // trim whitespace from each value
BE_ValuesFilterOut ( $list ; $remove )          // remove the values in $remove (inverse of FilterValues)
BE_ValuesContainsDuplicates ( $list )           // True if any dupes
BE_ValuesTimesDuplicated ( $list ; 2 )          // values that appear exactly twice
```

`BE_ValuesUnique` is handy to drop blank lines left by `BE_RegularExpression`'s `v` option over a list
(see the `.fmp12` filter example in `files-folders-zip.md`).

## In-memory arrays and stacks

When you need mutable, indexed data without records — held in plugin memory by name/handle:

```
# array (indexed, from a value list)
Set Variable [ $a ; BE_ArraySetFromValueList ( $valueList ) ]   // returns a handle
Set Variable [ $n ; BE_ArrayGetSize ( $a ) ]
Set Variable [ $v ; BE_ArrayGetValue ( $a ; 3 ) ]
Set Variable [ $r ; BE_ArrayChangeValue ( $a ; 3 ; "new" ) ]
Set Variable [ $r ; BE_ArrayDelete ( $a ) ]                     // free it when done

# stack (LIFO, by name)
BE_StackPush ( "undo" ; $state )
Set Variable [ $top ; BE_StackPop ( "undo" ) ]                  // returns + removes top
Set Variable [ $left ; BE_StackCount ( "undo" ) ]
```

⚠️ Arrays/stacks live in plugin memory for the session — clean up (`BE_ArrayDelete`/`BE_StackDelete`)
to avoid leaks in long-running solutions.

## Vector math (e.g. embedding similarity)

```
BE_VectorDotProduct ( $vecA ; $vecB )           // dot product of two number lists
BE_VectorEuclideanDistance ( $vecA ; $vecB )    // distance between two vectors
```

Useful for ranking AI embeddings client-side. (FM 2026 also has native semantic-find steps.)

## Notes

- `BE_FileMakerSQL` (internal SQL with INSERT/UPDATE/DELETE/DDL) lives in `system-and-containers.md`.
- Check `BE_GetLastError` after each call; jq/XPath/XSLT/regex syntax errors report there.
