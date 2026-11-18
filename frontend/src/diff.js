// Word-level diff via longest common subsequence. Returns [{t:"same"|"add"|"del", w}]
export function wordDiff(a, b) {
  const x = a.split(/\s+/), y = b.split(/\s+/);
  const dp = Array.from({ length: x.length + 1 }, () => new Array(y.length + 1).fill(0));
  for (let i = x.length - 1; i >= 0; i--)
    for (let j = y.length - 1; j >= 0; j--)
      dp[i][j] = x[i] === y[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out = []; let i = 0, j = 0;
  while (i < x.length && j < y.length) {
    if (x[i] === y[j]) { out.push({ t: "same", w: x[i] }); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) out.push({ t: "del", w: x[i++] });
    else out.push({ t: "add", w: y[j++] });
  }
  while (i < x.length) out.push({ t: "del", w: x[i++] });
  while (j < y.length) out.push({ t: "add", w: y[j++] });
  return out;
}
