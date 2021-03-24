# arch package builder docker action

This action builds arch packages stored as submodules and uploads them to S3

## Inputs

### `action`

**Required** The step to take either `build` or `package`

## Example usage

uses: actions/builder@v1
with:
  action: build
