# Data binding — groundwork, not a recipe book

**Read this first: everything in this file that is a Power Fx expression is
UNVERIFIED.** No expression here has been pasted into Power Apps Studio by this repo,
and no control it depends on is in [`controls.yaml`](controls.yaml). The file exists so
that when the paste tests in [`docs/test-plan.md`](../../../docs/test-plan.md) come
back, there is somewhere for the answers to land — not so the skill can start writing
data-bound screens today.

Three different levels of confidence appear below. Keep them apart:

| Marker | Means |
|---|---|
| **SCHEMA-VERIFIED** | Checked against the bundled `schema-v3.pa.yaml` in this repo, with the command to re-check it. Says the YAML is *legal*; says nothing about Studio. |
| **DOCUMENTED** | The function or property is in Microsoft's published reference. Real Power Fx; still never pasted from `.pa.yaml` here. |
| **UNVERIFIED** | A guess, an inference, or a shape nobody here has tried. |

Nothing in this file may be copied into `controls.yaml`. That file takes Studio results
only.

---

## 1. The `DataSources:` block — SCHEMA-VERIFIED

This is the one part with hard ground under it. `DataSources` is a real top-level key
of the pa.yaml v3.0 schema, alongside `App`, `Screens`, `ComponentDefinitions` and
`EditorState`:

- [`schema-v3.pa.yaml`](schema-v3.pa.yaml) line 17 — the root property
  `DataSources: { $ref: "#/definitions/DataSources-name-instance-map" }`
- line 453 — `DataSources-name-instance-map`, an object keyed by data source name
- line 457 — `DataSource-instance`, which is where the constraints live

What the schema actually permits, confirmed by running the bundled schema against
candidate documents:

```bash
python3 - <<'PY'
import yaml, jsonschema
schema = yaml.safe_load(open('skills/power-app-yaml/references/schema-v3.pa.yaml'))
V = jsonschema.Draft7Validator(schema)
for name, doc in {
    "Table, no Parameters":  {"DataSources": {"Requests": {"Type": "Table"}}},
    "Table + TableLogicalName": {"DataSources": {"Requests": {"Type": "Table", "Parameters": {"TableLogicalName": "Requests"}}}},
    "Actions": {"DataSources": {"GenerateDocument": {"Type": "Actions"}}},
    "Table + ConnectorId": {"DataSources": {"Requests": {"Type": "Table", "ConnectorId": "/providers/x"}}},
    "Type: SharePoint": {"DataSources": {"Requests": {"Type": "SharePoint"}}},
}.items():
    print(name, "->", "VALID" if not list(V.iter_errors(doc)) else "INVALID")
PY
```

Results, as of the bundled copy of the schema:

| Shape | Verdict |
|---|---|
| `Type: Table`, nothing else | **VALID** |
| `Type: Table` + `Parameters.TableLogicalName` | **VALID** |
| `Type: Actions`, nothing else | **VALID** |
| `Type: Table` + `ConnectorId` | **INVALID** |
| `Type: Actions` + `ConnectorId` | **INVALID** |
| `Type: Table` + any `Parameters` key other than `TableLogicalName` | **INVALID** |
| `Type: SharePoint` | **INVALID** — `Type` is an enum of exactly `Table` and `Actions` |

Two things worth knowing about that table:

1. **`ConnectorId` is declared and then forbidden.** `DataSource-instance` lists
   `ConnectorId` under `properties`, but both `oneOf` branches set
   `additionalProperties: false` without it, so any document carrying it fails the
   `oneOf`. That reads like an upstream bug rather than an intention. Either way, do
   not write `ConnectorId` — the bundled schema rejects it, and the linter's L1 layer
   will too.
2. **There is no SharePoint-shaped entry.** `Type` has two members and neither is a
   connector. `TableLogicalName` is Dataverse vocabulary. **UNVERIFIED:** how Studio
   actually serialises a SharePoint list into `DataSources:` — whether as a bare
   `Type: Table`, with some `Parameters` the published schema does not model, or not in
   `DataSources` at all. Do not guess this from the schema; read it off a real export
   (`python scripts/app_inventory.py <export>` prints the `DataSources:` entries of an
   app in one line each).

The minimum legal declaration of a list-shaped source is therefore:

```yaml
# UNVERIFIED as a Studio round-trip. SCHEMA-VERIFIED as legal pa.yaml v3.0.
# Paste test: none of the kit covers this -- see docs/test-plan.md, "DataSources block".
DataSources:
  Requests:
    Type: Table
  ArchiveRequests:
    Type: Table
  GenerateDocument:
    Type: Actions
Screens:
  ScrRequests:
    Children:
      - lblRequestsTitle:
          Control: Label@2.5.1
          Properties:
            Text: ="Requests"
            X: =40
            Y: =40
```

**The bigger unknown sits above all of this.** "Paste code" pastes *controls onto a
screen*. Whether it accepts a file whose top level carries `DataSources:` at all —
rather than ignoring the block, or refusing the paste — is untested. The safe reading
is that connections are made in Studio's own **Data** pane and the `DataSources:` block
is something an *export* contains, not something a paste creates. Treat adding a data
source as a manual Studio step until a test says otherwise.

---

## 2. Gallery `Items` — UNVERIFIED

**Blocked on:** `gallery.pa.yaml` (test plan row 1). If the `Gallery` control id will
not paste, nothing in this section can be written at all.

```text
UNVERIFIED  Gallery.Items over a whole list
    Items: =Requests

UNVERIFIED  ... sorted newest first          (SortOrder is DOCUMENTED Power Fx)
    Items: =Sort(Requests, Created, SortOrder.Descending)

UNVERIFIED  ... filtered to one status
    Items: =Filter(Requests, Status.Value = "Open")
```

`Status.Value` rather than `Status`: a SharePoint **choice** column comes through as a
record with a `.Value`, while a plain text column does not. Getting that wrong is the
most common reason a filter silently returns nothing. Which of your columns are choices
is a fact about your list, not about Power Apps — check it before writing the filter.

Inside the gallery's template, each row is `ThisItem`:

```text
UNVERIFIED  a Label inside the gallery template
    Text: =ThisItem.Title
    Text: =ThisItem.'Request Number'      # quote a column name containing a space
```

**UNVERIFIED and separately so:** how a gallery template is expressed in `.pa.yaml` at
all. A gallery in Studio holds a repeating template, and whether that appears as an
ordinary nested `Children:` list, as a wrapper control, or as something the paste path
cannot express is unknown here. `gallery.pa.yaml` deliberately tests a gallery with no
children first, because that question is downstream of "does the id paste".

---

## 3. Per-user filtering with `User().Email` — UNVERIFIED

**Blocked on:** `gallery.pa.yaml` (row 1).

`User()` is DOCUMENTED Power Fx and returns the signed-in user;
`User().Email` is their address. The pattern below assumes your list has a text column
holding the creator's email — written `CreateBy` here, but use whatever yours is called:

```text
UNVERIFIED  only my own records
    Items: =Filter(Requests, CreateBy = User().Email)

UNVERIFIED  ... same thing, resolved once in App.OnStart instead of per row
    OnStart:  =Set(varUserEmail, User().Email)
    Items:    =Filter(Requests, CreateBy = varUserEmail)

UNVERIFIED  mine, plus everything if I am an approver
    Items: =Filter(Requests, varIsApprover || CreateBy = varUserEmail)
```

Prefer the second form. It reads the user once instead of on every row, and it is the
shape [`extend-existing-app.md`](extend-existing-app.md) tells you to look for when
inventorying an app that already does this.

Three warnings, none of which a paste test will catch:

- **Case.** Email comparison in Power Fx `=` is not reliably case-insensitive across
  sources. If rows go missing, compare `Lower(CreateBy) = Lower(varUserEmail)` — at the
  cost of the next point.
- **Delegation.** SharePoint delegates a plain `=` on a text column but does **not**
  delegate `Lower(...)`. Beyond the delegation limit (500 rows by default, 2000 max)
  a non-delegable filter silently returns a truncated set — no error, just missing
  records. This is DOCUMENTED Microsoft behaviour, not something this repo has tested.
- **It is not security.** A client-side filter hides rows; it does not stop anyone
  reading the list. Real per-user restriction is SharePoint list permissions.

---

## 4. Two sites, two sets of lists — UNVERIFIED

A list on another team site is a **separate data source**, even when the list has the
same name and the same columns. There is no cross-site "same list" in Power Apps: you
add each one, and each gets its own name in `DataSources:`.

```yaml
# UNVERIFIED as a Studio round-trip. SCHEMA-VERIFIED as legal pa.yaml v3.0.
# Two same-shaped lists on two different sites are two entries, named apart.
DataSources:
  RequestsSiteA:
    Type: Table
  RequestsSiteB:
    Type: Table
Screens:
  ScrRequests:
    Children:
      - lblSiteLabel:
          Control: Label@2.5.1
          Properties:
            Text: =varActiveSiteName
            X: =40
            Y: =40
```

Studio itself picks the name when you add a connection, and it will disambiguate a
collision on its own — which is exactly why you should read the real names out of an
export rather than assume. To combine two same-shaped lists into one gallery:

```text
UNVERIFIED  one gallery over both sites
    Items: =Filter(RequestsSiteA, CreateBy = varUserEmail)

UNVERIFIED  ... concatenated, if the columns really do line up
    Items: =Filter(
              Table(RequestsSiteA, RequestsSiteB),
              CreateBy = varUserEmail
            )
```

The second form is the fragile one: it is not delegable, so it pulls both lists to the
client first, and it needs the column names to match exactly. A screen-level toggle that
swaps which single source the gallery reads is usually the better shape and stays
delegable.

---

## 5. Forms and `SubmitForm` — UNVERIFIED

**Blocked on:** `form.pa.yaml` (test plan row 2).

```text
UNVERIFIED  a form bound to a list, in new-record mode
    DataSource:  =Requests
    DefaultMode: =FormMode.New

UNVERIFIED  ... bound to the row a gallery has selected, for editing
    DataSource: =Requests
    Item:       =galRequests.Selected

UNVERIFIED  the save button
    OnSelect:  =SubmitForm(frmRequest)

UNVERIFIED  what happens after a successful save
    OnSuccess: =Navigate(ScrConfirmation); ResetForm(frmRequest)

UNVERIFIED  what happens after a failed one
    OnFailure: =Notify(frmRequest.Error, NotificationType.Error)
```

`SubmitForm`, `ResetForm`, `NewForm`, `EditForm` and `ViewForm` are DOCUMENTED Power Fx
functions; `DataSource`, `DefaultMode`, `Item`, `OnSuccess`, `OnFailure`, `Error` and
`LastSubmit` are DOCUMENTED properties of the form control. What is unverified is all of
it *expressed in `.pa.yaml` and applied by a paste*.

Two structural unknowns sit behind the form, and both matter more than the expressions:

- A real form's fields are **DataCard** children generated from the data source. The
  1P control-id enum mirrored in this repo lists `DataCard` and `TypedDataCard`, so they
  exist as ids — but whether a pasted form generates its own cards, requires them
  written out, or cannot be pasted at all is untested. `form.pa.yaml` tests a form with
  no children on purpose.
- `Item: =galRequests.Selected` is a reference to **another control by name**. If Studio
  renames either control on paste — which it does silently on a name collision — the
  reference breaks. This is the concrete reason the collision list from
  `scripts/app_inventory.py` matters before you paste anything into a real app.

---

## 6. `Patch` — UNVERIFIED

`Patch` needs no form control, which makes it the one section here whose only dependency
is a data source.

```text
UNVERIFIED  create a row
    OnSelect: =Patch(
                Requests,
                Defaults(Requests),
                { Title: txtTitle.Text,
                  CreateBy: varUserEmail,
                  Status: { Value: "Open" } }
              )

UNVERIFIED  update the row a gallery has selected
    OnSelect: =Patch(
                Requests,
                galRequests.Selected,
                { Status: { Value: "Approved" } }
              )

UNVERIFIED  create and keep the new row, so its ID can be used next
    OnSelect: =Set(varNewRequest,
                Patch(Requests, Defaults(Requests), { Title: txtTitle.Text })
              )
```

`{ Value: "Open" }` is the choice-column shape again — a plain string will be rejected
for a choice column and accepted for a text one. `Defaults(<source>)` is what makes it a
create rather than an update; leave it out and `Patch` needs an existing record.

---

## 7. Calling a Power Automate flow — UNVERIFIED

A flow appears in `DataSources:` as `Type: Actions` — that shape is **SCHEMA-VERIFIED**
above and is the one connector-ish thing the published schema does model. Calling it:

```text
UNVERIFIED  run a flow and keep what it returns
    OnSelect: =Set(varDocUrl, GenerateDocument.Run(varNewRequest.ID, varUserEmail))

UNVERIFIED  ... then open the document
    OnSelect: =Launch(varDocUrl)
```

The argument list is **entirely determined by the flow**, not by Power Apps: it is the
"Ask in PowerApps" / Power Apps trigger inputs of that flow, in the order the flow
declares them, and it changes whenever the flow changes. Nothing can be inferred about
it from this side, so nothing here should ever be written speculatively — read the flow.
`Set(varDocUrl, ...)` assumes the flow responds to Power Apps with a value; a
fire-and-forget flow returns nothing and the `Set` is pointless.

---

## What to do with any of this

1. **Do not write it into a screen yet.** Every section above is blocked on a control
   that has never pasted here. `scripts/pa_lint.py` will flag those controls at L2 and
   generate the isolated snippet; hand it over, do not bury it.
2. **Run the blocking test first.** The rows in
   [`docs/test-plan.md`](../../../docs/test-plan.md) are ordered so that Gallery and
   Form — which unblock most of this file — come first.
3. **When a test comes back, the control goes in `controls.yaml` and the expression
   does not.** The catalog records controls and properties. A Power Fx expression that
   worked once is a note for this file, upgraded from UNVERIFIED to a cited result with
   the Studio version beside it.
4. **An export beats all of it.** If you can download the app you are targeting,
   `python scripts/app_inventory.py <export>` prints its real `DataSources:` names and
   the variables its `App.OnStart` already sets, which replaces several guesses above
   with facts in one command.
