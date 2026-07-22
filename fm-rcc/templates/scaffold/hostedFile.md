# Hosted file — connection info

The hosted FileMaker file this engagement works against. Every script and
runbook in this project reads its connection details from this file — fill it in
during `workflow/01`, keep it current. The driver scripts parse the exact
`key - value` line format below; keep the format.

server  - <your-server.example.com>
file    - <YourDatabase.fmp12>
account - <api_account>
pass    - <fill in — read the credentials note first>

OData base URL: `https://<server>/fmi/odata/v4/<file-without-.fmp12>`

The export drop box for THIS file (see `workflow/02` — the standard
paste-in pair uses the values below as-is; a custom install records its own
names. The driver reads these instead of hardcoding them):

dropTable  - SAXML
dropLayout - SAXML
textField  - ResponseText

> **Note on credentials:** on a shared training sandbox it can be reasonable
> to keep the account and password in this file for reproducibility. On a
> real client project, credentials never get committed — keep the password
> in `.env` (gitignored) or a password manager, and leave the `pass` line
> as a pointer to where it lives.
