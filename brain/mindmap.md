---
slug: mindmap
title: Feature mindmap
role: feature mindmap
updated: "2026-10-13T05:37:39"
---

# Feature mindmap

## Feature mindmap

```mermaid
mindmap
  root((librime-stl))
    引擎
      去 Boost
        std::regex + PCRE 翻译层
        string_utils / signal / uuid / crc32 / scope_exit shim
      部署
        SchemaUpdate 只建 translator/dictionary
        schema/dependencies 拉额外词典
      组件
        Simplifier（option 门控滤镜）
        ScriptEncoder 动态组词
    词库 dict/
      luna_pinyin.dict.yaml（只放组不出的条目）
      essay.txt（词频，不裁剪）
      opencc/
        简繁与字形（t2s_full / t2hk / t2tw + .ocd2）
        原创转换表（variants*）
        emoji 扩展词典（vendored，默认关）
      两道门 check / smoke
    分发
      v…-rime-stack（引擎+词库）
      dict-…（纯数据修订）
      term-ime-dict tarball（rime-data）
