# Install OEM Checkbox providers

## Introduce

This is a tool to help you set up the test environment,
like installing the main package `checkbox-ng`,
and also other essential packages.

## Usage

1. Copy this folder to your computer.
2. Change directory to this folder.
3. Modify your information inside the `./conf/setting.conf`.
   1. `username`: Launchpad ID
   2. `ppa_password`:
      1. go to [launchpad](https://launchpad.net/people/+me/+archivesubscriptions/10011)
         and find the string between `https://%{yourname}:`
         and `@private-ppa…` is your ppa_password.
   3. `api_key`:
      1. Get your api key from [here](https://certification.canonical.com/me).
   4. `provider`: `stella`, `somerville` or `sutton`.
   5. `repository`: `stable`, `testing` or `daily`.
4. Run command `$ sh oem-qa-checkbox-installer.sh`.
5. Follow the instructions of the script.
6. Test environment setup done! Now you can run `stella-cli`, `somerville-cli`
   or `sutton-cli`. to test your DUT.
