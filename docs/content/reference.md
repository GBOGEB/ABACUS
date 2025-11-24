---
title: ABACUS and integrated reference
shortTitle: ABACUS reference
intro: 'Reference guide for ABACUS terms and cross-repo examples.'
type: reference
---

## Example: area-as-line (from morris.js examples)

Reference usage of an area chart behaving like a line (see examples in morris.js):

```js
Morris.Area({
  element: 'graph',
  behaveLikeLine: true,
  data: [
    {x: '2011 Q1', y: 3, z: 3},
    {x: '2011 Q2', y: 2, z: 1},
    {x: '2011 Q3', y: 2, z: 4},
    {x: '2011 Q4', y: 3, z: 3}
  ],
  xkey: 'x',
  ykeys: ['y', 'z'],
  labels: ['Y', 'Z']
});
```

## Cross-repo links
- [GBOGEB/ABACUS](https://github.com/GBOGEB/ABACUS)
- [GBOGEB/CODEX](https://github.com/GBOGEB/CODEX)
- [GBOGEB/morris.js](https://github.com/GBOGEB/morris.js)
