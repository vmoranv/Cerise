import { defineConfig } from 'rolldown';

export default defineConfig({
  input: 'src/index.ts',
  output: {
    dir: 'dist',
    format: 'esm',
  },
  // 2026 特性：内置 TS 支持，无需额外 plugin
  resolve: {
    // 自动识别 tsconfig.json 中的 paths 别名
    conditionNames: ['import', 'module', 'require'],
  },
  // 生产环境开启混淆 (Rolldown 1.0+ 稳定特性)
  minify: true, 
});