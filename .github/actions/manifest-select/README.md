## Purpose

This action simply convert the checkbox expend json output to a
webpage manifest selector.

## Usage

The input checkbox_expend is the output of command and
store one index.html at current folder.

```bash
checkbox-cli expand \
com.canonical.certification::client-cert-desktop-24-04 -f json \
> manifest.json
```

## Example caller workflow

```yaml
name: Deploy Checkbox Manifest to GitHub Pages

on:
  workflow_dispatch: # Allows manual triggering
  schedule:
    # Runs every Sunday at 00:00 UTC
    - cron: '0 0 * * SUN'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write # To push the generated index.html
      pages: write    # To deploy to GitHub Pages
      id-token: write # To authenticate with GitHub Pages

    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install canonical checkbox client
        run: |
          sudo add-apt-repository ppa:checkbox-dev/beta -y
          sudo apt-get update -qq
          sudo apt-get install \
               canonical-certification-client \
               checkbox-provider-gpgpu -qq -y

      - name: Generate manifest.json
        run: |
          checkbox-cli expand \
          com.canonical.certification::client-cert-desktop-24-04 -f json \
          > manifest.json

      - name: Generate GitHub Page (index.html)
        uses: canonical/oem-qa-tools/.github/actions/manifest-select@main
        with:
          checkbox_expend: manifest.json

      - name: Setup Pages
        uses: actions/configure-pages@v5
        with:
          enablement: true

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: './' # Uploads the entire current directory, which contains index.html

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```
