#!/bin/bash

set -e

export LC_ALL=C

FOLDER="$1"

SUITE="titan"
MANIFEST="spreedbox-$SUITE.manifest"
SHA256SUMS="SHA256SUMS"

if [ -z "$FOLDER" -o ! -d "$FOLDER" ]; then
	echo "Usage: $0 <release folder>"
	exit 1
fi

if [ ! -e "$FOLDER/$SHA256SUMS" ]; then
	echo "Error: $SHA256SUMS not found"
	exit 2
fi

VERSION=$(basename $FOLDER)
echo "Using $VERSION from $FOLDER ..."

(cd "$FOLDER" && sha256sum -c "$SHA256SUMS")

BASEPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )"

echo $BASEPATH
cp -avf "$FOLDER/$MANIFEST" "$BASEPATH/MANIFEST.txt"
cp -avf "$FOLDER/$SHA256SUMS" "$BASEPATH/SHA256SUMS"
echo "$VERSION" > "$BASEPATH/version.txt"

git add "$BASEPATH/version.txt"
git add "$BASEPATH/MANIFEST.txt"
git add "$BASEPATH/SHA256SUMS"
git diff --cached --exit-code || true

TAG="v$VERSION"

while true; do
	read -p "Do you wish to commit and tag $TAG now? " yn
    case $yn in
        [YyJj]*)
			break
			;;
        [Nn]*)
			echo "Aborted at your request!"
			exit
		;;
		*)
			echo "Please answer yes or no."
			;;
    esac
done

set -x
git commit -m "$VERSION"
git tag -a -s -m "$VERSION" "$TAG"
set +x

echo "Done. Version: $VERSION tagged as"

echo "Do not forget to push: 'git push && git push origin $TAG'"
