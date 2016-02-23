# Spreedbox Firmware image releases

This repository tracks checksums, package lists (manifest). These files are tagged with a signature and a version number which defines the Spreedbox firmare image release.

## Download

The downloads for the released images are found on the [Releases](https://github.com/spreedbox/spreedbox-firmware/releases) page.

## Manifest

The full list of all packages inside a firmware image are listed in the MANIFEST.txt file. This list can be used to track package additions, removals and updates accross releases.

## Validation of releases

The SHA256 check sum of the release image is found in the SHA256SUMS. It covers both the release image and the manifest for that release.

Releases are tagged and signed with Git by the release person. Use `git --verify-tag <version>` to validate.

## Firmware Upgrade

Normally it is not required to upgrade the firmware of your Spreedbox. Instead check out the [Software Upgrade](https://github.com/spreedbox/spreedbox/wiki/Software-Update) page for instructions to upgrade the software on your Spreedbox to the lastest.

If you want to use a new SD card or want to set up your Spreedbox clean from scratch, then this Firmware image is for you. After downloading the firmware disk image, please see [Firmware Upgrade](https://github.com/spreedbox/spreedbox/wiki/Firmware-Upgrade) at the [Spreedbox Wiki](https://github.com/spreedbox/spreedbox/wiki) on how to flash the new disk image to your Spreedbox.

