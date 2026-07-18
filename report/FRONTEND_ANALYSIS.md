# Frontend Analysis - Kairos

## Summary
- [Duplication issues](#duplication-issues)
- [Inconsistencies](#inconsistencies)
- [Possible improvements](#possible-improvements)
- [Fixes applied](#fixes-applied)

---

## Duplication issues

### 1. CSS - Duplicated utility classes

**Files involved:**
- `app/static/css/base-styles.css` (lines 400-450)
- `app/static/css/dark-theme.css` (lines 40-60)

**Problem:**
The following utility classes are defined in both files:
- `.gap-0` to `.gap-5`
- `.min-w-80`, `.min-w-140`, `.min-w-150`, `.min-w-180`, `.min-w-200`
- `.w-80`, `.w-100`
- `.mb-0` to `.mb-5`
- `.d-none`, `.d-block`, `.d-flex`, `.d-inline`, `.d-inline-block`
- `.visible`, `.invisible`

**Solution:**
Keep these classes only in `base-styles.css` and remove them from `dark-theme.css`.

### 2. CSS - Duplicated focus styles

**Files involved:**
- `app/static/css/base-styles.css` (lines 30-80)
- `app/static/css/dark-theme.css` (lines 200-230)

**Problem:**
`:focus-visible` styles are defined in both files with similar selectors.

**Solution:**
Centralize all focus styles in `base-styles.css` and keep only dark-theme-specific overrides in `dark-theme.css`.

### 3. CSS - Duplicated notification styles

**Files involved:**
- `app/static/css/base-styles.css` (lines 200-220, 500-520)
- `app/static/css/dark-theme.css` (lines 100-130)

**Problem:**
`.notification` styles appear twice in `base-styles.css` and are also present in `dark-theme.css`.

**Solution:**
Remove the duplicates in `base-styles.css` and keep a single consistent definition.

### 4. HTML - Duplicated action legends

**Files involved:**
- `app/templates/schedule.html` (lines 135-148)
- `app/templates/oncall.html` (lines 95-107)
- `app/templates/leave.html` (lines 70-77)

**Problem:**
Each template has a very similar "Action legend" section with example buttons.

**Solution:**
Create a reusable partial template `_action_legend.html`.

### 5. HTML - Duplicated ICS export buttons

**Files involved:**
- `app/templates/index.html` (lines 25-35)
- `app/templates/schedule.html` (lines 20-26)
- `app/templates/oncall.html` (lines 19-25)
- `app/templates/leave.html` (lines 19-25)
- `app/templates/admin/dashboard.html` (lines 92-100)

**Problem:**
ICS export buttons are duplicated across several templates with minor variations.

**Solution:**
Create a reusable partial template `_ics_export_buttons.html`.

### 6. HTML - Similar table structure

**Files involved:**
- `app/templates/schedule.html`
- `app/templates/oncall.html`
- `app/templates/leave.html`

**Problem:**
The table structure (container, caption, thead, tbody) is very similar.

**Solution:**
Create common CSS classes and possibly a Jinja2 macro for tables.

### 7. JavaScript - Duplicated confirmation code

**File involved:**
- `app/templates/schedule.html` (lines 90-130)
- `app/templates/oncall.html` (lines 70-85)
- `app/templates/leave.html` (line 57)

**Problem:**
Calls to `confirm()` or `Kairos.confirmActionAccessible()` are duplicated with similar messages.

**Solution:**
Systematically use `Kairos.confirmActionAccessible()` and standardize the messages.

---

## Inconsistencies

### 1. Use of `aria-label`

**Problem:**
- Some buttons have `aria-label`
- Others have `title`
- Some have neither

**Examples:**
- `schedule.html` line 15: `aria-label="Add a new shift"`
- `schedule.html` line 21: `aria-label="Export all shifts as iCalendar"`
- `leave.html` line 20: `title="Export all leave"` (no aria-label)

**Solution:**
Standardize on `aria-label` for every interactive element and add `title` as a fallback.

### 2. Inconsistent Bulma classes

**Problem:**
- Some templates use `is-flex` + `is-flex-wrap-wrap`
- Others use `is-flex is-flex-wrap-nowrap`
- Some don't use Bulma classes at all

**Solution:**
Standardize on the use of native Bulma classes.

### 3. Inconsistent HTML structure

**Problem:**
- Some templates have `<main role="main">`
- Others don't
- Some have sections with `aria-labelledby`
- Others don't

**Solution:**
Standardize the HTML structure with consistent ARIA roles.

### 4. Use of `role="group"`

**Problem:**
- `schedule.html` uses `role="group"` for buttons
- `oncall.html` doesn't use it
- `leave.html` doesn't use it

**Solution:**
Add `role="group"` to every button group.

### 5. Inconsistent confirmation messages

**Problem:**
- Some use the native `confirm()`
- Others use `Kairos.confirmActionAccessible()`
- Messages vary (capitalization, punctuation)

**Examples:**
- `oncall.html` line 29: `confirm('Are you SURE you want to delete ALL on-call shifts?')`
- `schedule.html` line 32: `Kairos.confirmActionAccessible('Are you SURE you want to delete ALL shifts?')`

**Solution:**
Systematically use `Kairos.confirmActionAccessible()` with standardized messages.

---

## Possible improvements

### 1. CSS

1. **Centralize CSS variables**
   - Create a `_variables.css` file with every variable
   - Import this file into every other CSS file

2. **Organize CSS by component**
   - Create separate files for:
     - `buttons.css`
     - `tables.css`
     - `forms.css`
     - `cards.css`
     - `modals.css`

3. **Use Sass mixins**
   - Convert the CSS to SCSS to use mixins
   - Reduce code duplication

### 2. HTML/Templates

1. **Create partial templates**
   - `_action_legend.html`
   - `_ics_export_buttons.html`
   - `_table_container.html`
   - `_pagination.html` (already exists)

2. **Use Jinja2 macros**
   - For repetitive forms
   - For tables
   - For stat cards

3. **Improve accessibility**
   - Add `aria-label` to every interactive element
   - Add `aria-describedby` where needed
   - Check the tab order

### 3. JavaScript

1. **Centralize confirmation logic**
   - Systematically use `Kairos.confirmActionAccessible()`
   - Standardize the messages

2. **Improve error handling**
   - Use `Kairos.announceToScreenReader()` for every error
   - Standardize error messages

3. **Optimize event listeners**
   - Use event delegation where possible
   - Avoid code duplication

---

## Fixes applied

### 1. CSS

- [ ] Removed duplicated utility classes in `dark-theme.css`
- [ ] Removed duplicated notification styles in `base-styles.css`
- [ ] Centralized focus styles in `base-styles.css`
- [ ] Organized CSS into clear sections

### 2. HTML/Templates

- [ ] Created `_action_legend.html`
- [ ] Created `_ics_export_buttons.html`
- [ ] Standardized use of `aria-label`
- [ ] Standardized use of `role="group"`
- [ ] Standardized HTML structure

### 3. JavaScript

- [ ] Replaced every `confirm()` with `Kairos.confirmActionAccessible()`
- [ ] Standardized confirmation messages
- [ ] Optimized event listeners

---

## Statistics

- **HTML files analyzed:** 46
- **Lines of HTML code:** ~4676
- **CSS files analyzed:** 3
- **Lines of CSS code:** ~24843
- **JS files analyzed:** 1
- **Lines of JS code:** 673

---

## Tools used

- `grep` to search for duplication
- `wc` to count lines
- Manual file analysis
