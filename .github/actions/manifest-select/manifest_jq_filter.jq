# Escape HTML entities for safe HTML output
def escapehtml:
  gsub("&"; "&amp;") | gsub("<"; "&lt;") | gsub(">"; "&gt;") | gsub("\""; "&quot;") | gsub("'"; "&#39;");

# Create checkbox input element string with unique id and data-id for json export
def toCheckboxInput(item):
  "<input type=\"checkbox\" id=\"" + (item.id|escapehtml) + "\" data-id=\"" + (item.id|escapehtml) + "\" + checked>";

# Create a table row with _name and checkbox columns
def toTableRow(item):
  "<tr><td class=\"p-table__cell--top p-table__cell--dark\">" + (item._name|escapehtml) + "</td><td class=\"p-table__cell--top u-align--center\">" + (toCheckboxInput(item)) + "</td></tr>";

# Create HTML group section for all items having same _prompt value
def groupHtml(groupKey; items):
  "<h3 class=\"p-heading--4\">" + ((groupKey // "Does this machine have this piece of hardware?") | tostring | escapehtml) + "</h3>" +
  "<table class=\"p-table p-table--mobile-card u-full-width u-no-padding--bottom\">" +
  "<thead><tr><th class=\"p-table__header\">Manifest Entry</th><th class=\"p-table__header u-align--center\">Checked</th></tr></thead>" +
  "<tbody>" +
  (map(toTableRow(items)) | join("")) +
  "</tbody></table><br>";

# The embedded JavaScript that enables exporting the selection to JSON and downloading
def jsScript:
  "<script>
    function download(filename, text) {
      var element = document.createElement('a');
      element.setAttribute('href', 'data:text/json;charset=utf-8,' + encodeURIComponent(text));
      element.setAttribute('download', filename);
      element.style.display = 'none';
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    }
    function exportToJson() {
      var checkboxes = document.querySelectorAll('input[type=\"checkbox\"]');
      var result = {};
      checkboxes.forEach(function(cb) {
        var id = cb.getAttribute('data-id');
        result[id] = cb.checked;
      });
      var jsonStr = JSON.stringify(result, null, 2);
      download('machine-manifest.json', jsonStr);
    }
  </script>";

# Main filter composing the complete HTML page
(
"<!DOCTYPE html>
<html>
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Checkbox Manifest Viewer</title>
  <!-- Vanilla Framework CSS -->
  <link rel=\"stylesheet\" href=\"https://assets.ubuntu.com/v1/vanilla-framework-version-3.14.0.min.css\">
  <!-- Google Fonts for Inter -->
  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">
  <style>
      body {
          font-family: 'Inter', sans-serif;
          background-color: var(--p-color-grey-100); /* Using Vanilla's CSS variables for background */
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          padding: var(--p-spacing-medium); /* Equivalent to p-4 */
      }
      .main-container {
          background-color: var(--p-color-white);
          padding: var(--p-spacing-x-large); /* Equivalent to p-8 */
          border-radius: var(--p-border-radius-large); /* Equivalent to rounded-lg */
          box-shadow: var(--p-shadow--200); /* Equivalent to shadow-xl */
          width: 100%;
          max-width: 64rem; /* Custom max-width for md:max-w-4xl (approx 1024px) */
          overflow-x: auto;
      }
      .p-table__cell--dark {
          background-color: var(--p-color-white); /* Ensure table cells are white if the table itself is */
      }
      .p-table tbody tr:hover {
          background-color: var(--p-color-grey-000); /* Light hover effect for table rows */
      }
      .button-container {
        display: flex;
        justify-content: center;
        margin-top: var(--p-spacing-x-large);
      }
  </style>
</head>
<body>
  <div class=\"main-container\">
    <h1 class=\"p-heading--1 u-text--muted u-align--center u-margin-bottom--x-large\">Checkbox Manifest Entries</h1>
    <div class=\"overflow-x-auto\">" +
(
      # Group input array by _prompt and create a section per group
      group_by(._prompt) | map(
        (.[0]._prompt) as $key |
        groupHtml($key; .)
      ) | join("\n")
) +
"<div class=\"button-container\"><button class=\"p-button--positive u-no-margin--bottom\" onclick=\"exportToJson()\">Export to JSON</button>" +
jsScript +
"</div></div></body>
</html>"
)

