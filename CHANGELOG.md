# CHANGELOG


## v0.2.0 (2025-05-21)

### Continuous Integration

- Add semantic release configuration (and use pyproject version)
  ([`fbba8b7`](https://github.com/Monadical-SAS/cubbi/commit/fbba8b7613c76c6a1ae21c81d9f07697320f6d10))

- Try fixing the dynamic_import issue
  ([`252d8be`](https://github.com/Monadical-SAS/cubbi/commit/252d8be735e6d18761c42e9c138ccafde89fd6ee))

- Try fixing the dynamic_import issue (2, force adding pyproject.toml)
  ([`31e09bc`](https://github.com/Monadical-SAS/cubbi/commit/31e09bc7ba8446508a90f5a9423271ac386498fe))

### Documentation

- Add information for uvx
  ([`ba852d5`](https://github.com/Monadical-SAS/cubbi/commit/ba852d502eea4fc558c0f96d9015436101d5ef43))

- Add mit license
  ([`13c896a`](https://github.com/Monadical-SAS/cubbi/commit/13c896a58d9bc6f25b0688f9ae7117ae868ae705))

- Update classifiers
  ([`5218bb1`](https://github.com/Monadical-SAS/cubbi/commit/5218bb121804c440dc69c9d932787ed6d54b90f5))

- Update README
  ([`15d86d2`](https://github.com/Monadical-SAS/cubbi/commit/15d86d25e74162153c26d6c254059f24d46c4095))

### Features

- **cubbix**: Add --no-shell in combination with --run to not drop a shell and exit when the command
  is done
  ([`75daccb`](https://github.com/Monadical-SAS/cubbi/commit/75daccb3662d059d178fd0f12026bb97f29f2452))


## v0.1.0-rc.1 (2025-04-18)

### Bug Fixes

- Mcp tests
  ([`3799f04`](https://github.com/Monadical-SAS/cubbi/commit/3799f04c1395d3b018f371db0c0cb8714e6fb8b3))

- Osx tests on volume
  ([`7fc9cfd`](https://github.com/Monadical-SAS/cubbi/commit/7fc9cfd8e1babfa069691d3b7997449535069674))

- Remove double connecting to message
  ([`e36f454`](https://github.com/Monadical-SAS/cubbi/commit/e36f4540bfe3794ab2d065f552cfb9528489de71))

- Remove the "mc stop" meant to be in the container, but not implemented
  ([`4f54c0f`](https://github.com/Monadical-SAS/cubbi/commit/4f54c0fbe7886c8551368b4b35be3ad8c7ae49ab))

- **cli**: Rename MAI->MC
  ([`354834f`](https://github.com/Monadical-SAS/cubbi/commit/354834fff733c37202b01a6fc49ebdf5003390c1))

- **goose**: Add ping, nano and vim to the default image
  ([`028bd26`](https://github.com/Monadical-SAS/cubbi/commit/028bd26cf12e181541e006650b58d97e1d568a45))

- **goose**: Always update the file
  ([`b1aa415`](https://github.com/Monadical-SAS/cubbi/commit/b1aa415ddee981dc1278cd24f7509363b9c54a54))

- **goose**: Ensure configuration is run as user
  ([`cfa7dd6`](https://github.com/Monadical-SAS/cubbi/commit/cfa7dd647d1e4055bf9159be2ee9c2280f2d908e))

- **goose**: Install latest goose version, do not use pip
  ([`7649173`](https://github.com/Monadical-SAS/cubbi/commit/7649173d6c8a82ac236d0f89263591eaa6e21a20))

- **goose**: Remove MCP_HOST and such, this is not how mcp works
  ([`d42af87`](https://github.com/Monadical-SAS/cubbi/commit/d42af870ff56112b4503f2568b8a5b0f385c435c))

- **goose**: Rename mai to mc, add initialization status
  ([`74c723d`](https://github.com/Monadical-SAS/cubbi/commit/74c723db7b6b7dd57c4ca32a804436a990e5260c))

- **langfuse**: Fix goose langfuse integration (wrong env variables)
  ([`e36eef4`](https://github.com/Monadical-SAS/cubbi/commit/e36eef4ef7c2d0cbdef31704afb45c50c4293986))

- **mc**: Fix runtime issue when starting mc
  ([`6f08e2b`](https://github.com/Monadical-SAS/cubbi/commit/6f08e2b274b67001694123b5bb977401df0810c6))

- **mcp**: Fix UnboundLocalError: cannot access local variable 'container_name' where it is not
  associated with a value
  ([`deff036`](https://github.com/Monadical-SAS/cubbi/commit/deff036406d72d55659da40520a3a09599d65f07))

- **session**: Ensure a session connect only to the mcp server passed in --mcp
  ([`5d674f7`](https://github.com/Monadical-SAS/cubbi/commit/5d674f750878f0895dc1544620e8b1da4da29752))

- **session**: Fix session status display
  ([`092f497`](https://github.com/Monadical-SAS/cubbi/commit/092f497ecc19938d4917a18441995170d1f68704))

- **ssh**: Do not enable ssh automatically
  ([`f32b3dd`](https://github.com/Monadical-SAS/cubbi/commit/f32b3dd269d1a3d6ebaa2e7b2893f267b5175b20))

- **uid**: Correctly pass uid/gid to project
  ([`e25e30e`](https://github.com/Monadical-SAS/cubbi/commit/e25e30e7492c6b0a03017440a18bb2708927fc19))

- **uid**: Use symlink instead of volume for persistent volume in the container
  ([`a74251b`](https://github.com/Monadical-SAS/cubbi/commit/a74251b119d24714c7cc1eaadeea851008006137))

### Chores

- Remove unnecessary output
  ([`30c6b99`](https://github.com/Monadical-SAS/cubbi/commit/30c6b995cbb5bdf3dc7adf2e79d8836660d4f295))

- Update doc and add pre-commit
  ([`958d87b`](https://github.com/Monadical-SAS/cubbi/commit/958d87bcaeed16210a7c22574b5e63f2422af098))

### Continuous Integration

- Add ci files ([#11](https://github.com/Monadical-SAS/cubbi/pull/11),
  [`3850bc3`](https://github.com/Monadical-SAS/cubbi/commit/3850bc32129da539f53b69427ddca85f8c5f390a))

* ci: add ci files

* fix: add goose image build

### Documentation

- Add --run option examples to README
  ([`6b2c1eb`](https://github.com/Monadical-SAS/cubbi/commit/6b2c1ebf1cd7a5d9970234112f32fe7a231303f9))

- Prefer mcx alias in README examples
  ([`9c21611`](https://github.com/Monadical-SAS/cubbi/commit/9c21611a7fa1497f7cbddb1f1b4cd22b4ebc8a19))

- **mcp**: Add specification for MCP server support
  ([`20916c5`](https://github.com/Monadical-SAS/cubbi/commit/20916c5713b3a047f4a8a33194f751f36e3c8a7a))

- **readme**: Remove license part
  ([`1c538f8`](https://github.com/Monadical-SAS/cubbi/commit/1c538f8a59e28888309c181ae8f8034b9e70a631))

- **readme**: Update README to update tool call
  ([`a4591dd`](https://github.com/Monadical-SAS/cubbi/commit/a4591ddbd863bc6658a7643d3f33d06c82816cae))

### Features

- First commit
  ([`fde6529`](https://github.com/Monadical-SAS/cubbi/commit/fde6529d545b5625484c5c1236254d2e0c6f0f4d))

- **cli**: Auto connect to a session
  ([`4a63606`](https://github.com/Monadical-SAS/cubbi/commit/4a63606d58cc3e331a349974e9b3bf2d856a72a1))

- **cli**: Auto mount current directory as /app
  ([`e6e3c20`](https://github.com/Monadical-SAS/cubbi/commit/e6e3c207bcee531b135824688adf1a56ae427a01))

- **cli**: More information when closing session
  ([`08ba1ab`](https://github.com/Monadical-SAS/cubbi/commit/08ba1ab2da3c24237c0f0bc411924d8ffbe71765))

- **cli**: Phase 1 - local cli with docker integration
  ([`6443083`](https://github.com/Monadical-SAS/cubbi/commit/64430830d883308e4d52e17b25c260a0d5385141))

- **cli**: Separate session state into its own session.yaml file
  ([`7736573`](https://github.com/Monadical-SAS/cubbi/commit/7736573b84c7a51eaa60b932f835726b411ca742))

- **cli**: Support to join external network
  ([`133583b`](https://github.com/Monadical-SAS/cubbi/commit/133583b941ed56d1b0636277bb847c45eee7f3b8))

- **config**: Add global user configuration for the tool
  ([`dab783b`](https://github.com/Monadical-SAS/cubbi/commit/dab783b01d82bcb210b5e01ac3b93ba64c7bc023))

- langfuse - default driver - and api keys

- **config**: Ensure config is correctly saved
  ([`deb5945`](https://github.com/Monadical-SAS/cubbi/commit/deb5945e40d55643dca4e1aa4201dfa8da1bfd70))

- **gemini**: Support for gemini model
  ([`2f9fd68`](https://github.com/Monadical-SAS/cubbi/commit/2f9fd68cada9b5aaba652efb67368c2641046da5))

- **goose**: Auto add mcp server to goose configuration when starting a session
  ([`7805aa7`](https://github.com/Monadical-SAS/cubbi/commit/7805aa720eba78d47f2ad565f6944e84a21c4b1c))

- **goose**: Optimize init status
  ([`16f59b1`](https://github.com/Monadical-SAS/cubbi/commit/16f59b1c408dbff4781ad7ccfa70e81d6d98f7bd))

- **goose**: Update config using uv script with pyyaml
  ([#6](https://github.com/Monadical-SAS/cubbi/pull/6),
  [`9e742b4`](https://github.com/Monadical-SAS/cubbi/commit/9e742b439b7b852efa4219850f8b67c143274045))

- **keys**: Pass local keys to the session by default
  ([`f83c49c`](https://github.com/Monadical-SAS/cubbi/commit/f83c49c0f340d1a3accba1fe1317994b492755c0))

- **llm**: Add default model/provider to auto configure the driver
  ([#7](https://github.com/Monadical-SAS/cubbi/pull/7),
  [`5b9713d`](https://github.com/Monadical-SAS/cubbi/commit/5b9713dc2f7d7c25808ad37094838c697c056fec))

- **mc**: Support for uid/gid, and use default current user
  ([`a51115a`](https://github.com/Monadical-SAS/cubbi/commit/a51115a45d88bf703fb5380171042276873b7207))

- **mcp**: Add inspector
  ([`d098f26`](https://github.com/Monadical-SAS/cubbi/commit/d098f268cd164e9d708089c9f9525a940653c010))

- **mcp**: Add the possibility to have default mcp to connect to
  ([`4b0461a`](https://github.com/Monadical-SAS/cubbi/commit/4b0461a6faf81de1e1b54d1fe78fea7977cde9dd))

- **mcp**: Ensure inner mcp environemnt variables are passed
  ([`0d75bfc`](https://github.com/Monadical-SAS/cubbi/commit/0d75bfc3d8e130fb05048c2bc8a674f6b7e5de83))

- **mcp**: First docker proxy working
  ([`0892b6c`](https://github.com/Monadical-SAS/cubbi/commit/0892b6c8c472063c639cc78cf29b322bb39f998f))

- **mcp**: Improve inspector reliability over re-run
  ([`3ee8ce6`](https://github.com/Monadical-SAS/cubbi/commit/3ee8ce6338c35b7e48d788d2dddfa9b6a70381cb))

- **mcp**: Initial version of mcp
  ([`212f271`](https://github.com/Monadical-SAS/cubbi/commit/212f271268c5724775beceae119f97aec2748dcb))

- **project**: Explicitely add --project to save information in /mc-config across run.
  ([`3a182fd`](https://github.com/Monadical-SAS/cubbi/commit/3a182fd2658c0eb361ce5ed88938686e2bd19e59))

Containers are now isolated by default.

- **run**: Add --run command
  ([`33d90d0`](https://github.com/Monadical-SAS/cubbi/commit/33d90d05311ad872b7a7d4cd303ff6f7b7726038))

- **ssh**: Make SSH server optional with --ssh flag
  ([`5678438`](https://github.com/Monadical-SAS/cubbi/commit/56784386614fcd0a52be8a2eb89d2deef9323ca1))

- Added --ssh flag to session create command - Modified mc-init.sh to check MC_SSH_ENABLED
  environment variable - SSH server is now disabled by default - Updated README.md with new flag
  example - Fixed UnboundLocalError with container_name in exception handler

- **volume**: Add mc config volume command
  ([`2caeb42`](https://github.com/Monadical-SAS/cubbi/commit/2caeb425518242fbe1c921b9678e6e7571b9b0a6))

- **volume**: Add the possibilty to mount local directory into the container (like docker volume)
  ([`b72f1ee`](https://github.com/Monadical-SAS/cubbi/commit/b72f1eef9af598f2090a0edae8921c16814b3cda))

### Refactoring

- Move drivers directory into mcontainer package
  ([`307eee4`](https://github.com/Monadical-SAS/cubbi/commit/307eee4fcef47189a98a76187d6080a36423ad6e))

- Relocate goose driver to mcontainer/drivers/ - Update ConfigManager to dynamically scan for driver
  YAML files - Add support for mc-driver.yaml instead of mai-driver.yaml - Update Driver model to
  support init commands and other YAML fields - Auto-discover drivers at runtime instead of
  hardcoding them - Update documentation to reflect new directory structure

- Reduce amount of data in session.yaml
  ([`979b438`](https://github.com/Monadical-SAS/cubbi/commit/979b43846a798f1fb25ff05e6dc1fc27fa16f590))

- Rename driver to image, first pass
  ([`51fb79b`](https://github.com/Monadical-SAS/cubbi/commit/51fb79baa30ff479ac5479ba5ea0cad70bbb4c20))

- Rename project to cubbi
  ([`12d77d0`](https://github.com/Monadical-SAS/cubbi/commit/12d77d0128e4d82e5ddc1a4ab7e873ddaa22e130))

### Testing

- Add unit tests
  ([`7c46d66`](https://github.com/Monadical-SAS/cubbi/commit/7c46d66b53ac49c08458bc5d72e636e7d296e74f))
