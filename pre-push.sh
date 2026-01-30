#!/bin/bash
echo "Copying dependency files to root..."
cp server/requirements.txt requirements.txt
echo "Building frontend..."
pushd client
pnpm install
pnpm build
popd
echo "Done! Ready to push to Cloud Foundry."