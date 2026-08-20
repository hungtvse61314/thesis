# Node.js 23.7.0 setup

The frontend is configured for Node.js `23.7.x` and npm 10+.

## Clean installation

```bash
cd frontend
rm -rf node_modules
npm ci
npm run dev
```

The npm scripts invoke Vite through its real package entry:

```bash
node ./node_modules/vite/bin/vite.js
```

This avoids failures caused by a damaged or incorrectly extracted `node_modules/.bin/vite` symlink.

Do not copy or unzip a prebuilt `node_modules` directory. Install dependencies locally with `npm ci`.
