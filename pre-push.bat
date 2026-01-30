@echo off
echo Copying dependency files to root...
copy server\requirements.txt requirements.txt
echo Building frontend...
pushd client
call pnpm install
call pnpm build
popd
echo Done! Ready to push to Cloud Foundry.