#! /usr/bin/env python3
import json
import sys
from collections import Counter

def debug(*args):
    if False:
        print(*args)

manifestpath = sys.argv[1]
debug(f"reading manifest from {manifestpath}")

outputpath = sys.argv[2]
debug(f"will write expectations.json to {outputpath}")

with open(manifestpath, "r") as f:
    manifest = json.load(f)

th = manifest["items"]["testharness"]
debug(th.keys())

def extract_test_paths(parent, tree) -> list[str]:
    res : list[str] = []
    for path, v in tree.items():
        if isinstance(v, list):
            debug(f"test: {parent}/{path}")
            res.append(f"{parent}/{path}")
        else:
            debug(f"subdir: {parent}/{path} {v}")
            res.extend(extract_test_paths(f"{parent}/{path}", v))
    return res

def extract_test_paths_top_level(d: str) -> list[str]:
    return extract_test_paths(d, th[d])

def find_and_insert(parent: dict, edges):
    assert edges

    if len(edges) == 1:
        parent[edges[0]] = True
        return
    if edges[0] not in parent:
        parent[edges[0]] = {}
    dir = parent[edges[0]]
    find_and_insert(dir, edges[1:])

all_paths: list[str] = []

# ## AbortSignal

#     * `AbortController`

#     * `AbortSignal`


# ```
# +dom/abort/*
# -dom/abort/reason-constructor.html
# ```

dom = extract_test_paths_top_level("dom")
debug("\n".join(dom))
all_paths.extend(p for p in dom if p.startswith("dom/abort/") and not p == "dom/abort/reason-constructor.html")

# ## Web Crypto API

#     * Crypto

#     * CryptoKey

#     * SubtleCrypto

#     * globalThis.crypto


# ```
# +WebCryptoAPI/*
# -historical.any.*
# -algorithm-discards-context.https.window.*
# ```

crypto = extract_test_paths_top_level("WebCryptoAPI")
debug("\n".join(crypto))
all_paths.extend(
    p for p in crypto
    if not p.endswith("historical.any.js") and not p.endswith("algorithm-discards-context.https.window.js"))

# ## Console

#     * globalThis.console


# ```
# +console/*
# ```

# Tests are very sparse, and so is spec - it is unclear what side-effects `console.log` should have across runtimes.

console = extract_test_paths_top_level("console")
debug("\n".join(console))
all_paths.extend(console)


# ## Streams

#     * ByteLengthQueuingStrategy

#     * CountQueuingStrategy

#     * ReadableByteStreamController

#     * ReadableStream

#     * ReadableStreamBYOBReader

#     * ReadableStreamBYOBRequest

#     * ReadableStreamDefaultController

#     * ReadableStreamDefaultReader

#     * TransformStream

#     * TransformStreamDefaultController

#     * WritableStream

#     * WritableStreamDefaultController

#     * WritableStreamDefaultWriter


# ```
# +streams/*
# -streams/readable-streams/cross-realm-crash.window.html
# ```

# `streams/transferable/*` needs investigation.

streams = extract_test_paths_top_level("streams")
debug("\n".join(streams))
all_paths.extend(
    p for p in streams
    if not p.endswith("readable-streams/cross-realm-crash.window.html"))

# ## (De)compression streams

#     * CompressionStream

#     * DecompressionStream


# ```
# +compression/*
# ```

compression = extract_test_paths_top_level("compression")
debug("\n".join(compression))
all_paths.extend(compression)


# ## Text encoding

#     * TextDecoder

#     * TextDecoderStream

#     * TextEncoder

#     * TextEncoderStream


# ```
# +encoding/*
# -encoding/streams/realms.window.html
# -encoding/streams/invalid-realm.window.html
# -encoding/unsupported-encodings.any.*
# -encoding/single-byte-decoder.window.html
# -encoding/unsupported-labels.window.html
# ```

encoding = extract_test_paths_top_level("encoding")
debug("\n".join(encoding))
all_paths.extend(
    p for p in encoding
    if p not in [
        "encoding/streams/realms.window.html",
        "encoding/streams/invalid-realm.window.html",
        "encoding/unsupported-encodings.any.js",
        "encoding/single-byte-decoder.window.html",
        "encoding/unsupported-labels.window.html"])

# TODO: probably all of the html files should be excluded.

# ## URL

#     * URL

#     * URLSearchParams


# ```
# +url/*
# -url/url-setters-a-area.window.html
# -url/a-element-origin.html
# -url/a-element.html
# -url/data-uri-fragment.html
# -url/failure.html
# ```

# Note, a lot of tests in this directory also test using `<a>` and `<area>` tags from HTML. It would be good to split those into seperate files.

url = extract_test_paths_top_level("url")
debug("\n".join(url))
all_paths.extend(
    p for p in url
    if p not in [
        "url/url-setters-a-area.window.html",
        "url/a-element-origin.html",
        "url/a-element.html",
        "url/data-uri-fragment.html",
        "url/failure.html"])

# ## URLPattern

#     * URLPattern


# ```
# +urlpattern/urlpattern.any.*
# +urlpattern/urlpattern-https.any.*
# +urlpattern/urlpattern-hasregexpgroups.any.*
# ```

urlpattern = extract_test_paths_top_level("urlpattern")
debug("\n".join(urlpattern))
all_paths.extend(
    p for p in urlpattern
    if p not in [
        "urlpattern/urlpattern-https.any.js",
        "urlpattern/urlpattern-hasregexpgroups.any.js",
        "urlpattern/urlpattern.any.js"])

# ## File API

#     * Blob

#     * File


# ```
# +FileAPI/blob/*
# -FileAPI/blob/Blob-constructor-dom.window.html
# +FileAPI/file/*
# -FileAPI/file/send-file-form-*
# +FileAPI/url/url-format.any.*
# +FileAPI/url/url-with-fetch.any.*
# +FileAPI/unicode.html
# ```

# A lot of these tests rely on FileReader existing. Should we add this?

fileapi = extract_test_paths_top_level("FileAPI")
debug("\n".join(fileapi))
all_paths.extend(
    p for p in fileapi
    if
        (p.startswith("FileAPI/blob/") and not p == "FileAPI/blob/Blob-constructor-dom.window.js") or
        (p.startswith("FileAPI/file/") and not p.startswith("FileAPI/file/send-file-form-")) or
        p in [
            "FileAPI/url/url-format.any.js",
            "FileAPI/url/url-with-fetch.any.js",
            "FileAPI/unicode.html"])

# ## Structured Clone

#     * `structuredClone`


# More analysis needed: to be done by [@andreubotella](https://github.com/andreubotella). [web-platform-tests/wpt#49282](https://github.com/web-platform-tests/wpt/pull/49282)
# ## DOMException

#     * `DOMException`


# ```
# +webidl/ecmascript-binding/es-exceptions/DOMException-*
# ```

webidl = extract_test_paths_top_level("webidl")
debug("\n".join(webidl))
all_paths.extend(
    p for p in webidl
    if p.startswith("webidl/ecmascript-binding/es-exceptions/DOMException-"))

# ## WASM

#     * `WebAssembly`


# ```
# +wasm/*
# -wasm/serialization/module/*
# ```

# We need to write some dedicated tests for wasm structured clone that do not involve DOM / HTML.

wasm = extract_test_paths_top_level("wasm")
debug("\n".join(wasm))
all_paths.extend(
    p for p in wasm
    if not p.startswith("wasm/serialization/module/"))

# ## navigator

#     * `navigator`


# No existing tests that we can use.

# Create a new test for just `user-agent` to check it's a string. maybe also check that `fetch` sets the `user-agent` test.
# ## performance.now

#     * `performance.now`


# ```
# +hr-time/idlharness.any.*
# +hr-time/basic.any.*
# +hr-time/monotonic-clock.any.*
# ```

hrtime = extract_test_paths_top_level("hr-time")
debug("\n".join(hrtime))
all_paths.extend(
    p for p in hrtime
    if p in [
        "hr-time/idlharness.any.js",
        "hr-time/basic.any.js",
        "hr-time/monotonic-clock.any.js"])

# ## queueMicrotask

#     * `queueMicrotask`


# ```
# +html/webappapis/microtask-queuing/queue-microtask.any.*
# +html/webappapis/microtask-queuing/queue-microtask-exceptions.any.*
# ```

# ## `setInterval`/`setTimeout`

#     * `setInterval`

#     * `clearInterval`

#     * `setTimeout`

#     * `clearTimeout`


# ```
# +html/webappapis/timers/*
# -html/webappapis/timers/setinterval-cross-realm-callback-report-exception.html
# -html/webappapis/timers/settimeout-cross-realm-callback-report-exception.html
# ```

# ## `atob`/`btoa`

#     * `atob`

#     * `btoa`


# ```
# +html/webappapis/atob/*
# ```

html = extract_test_paths_top_level("html")
debug("\n".join(html))
all_paths.extend(
    p for p in html
    if p in [
        "html/webappapis/microtask-queuing/queue-microtask.any.js",
        "html/webappapis/microtask-queuing/queue-microtask-exceptions.any.js"] or
    (p.startswith("html/webappapis/timers/") and not p.endswith("cross-realm-callback-report-exception.html")) or
    p.startswith("html/webappapis/atob/"))


# ## `FormData`

# (`constructor.any.js` depends on what we decide to do with the arguments, see [#63](https://github.com/WinterTC55/proposal-minimum-common-api/issues/63))

# ```
# +xhr/formdata
# -xhr/formdata/append-formelement.html
# -xhr/formdata/constructor-formelement.html
# -xhr/formdata/constructor-submitter-coordinate.html
# -xhr/formdata/constructor-submitter.html
# -xhr/formdata/delete-formelement.html
# -xhr/formdata/get-formelement.html
# -xhr/formdata/has-formelement.html
# -xhr/formdata/set-formelement.html
# ```

xhr = extract_test_paths_top_level("xhr")
debug("\n".join(xhr))
all_paths.extend(
    p for p in xhr
    if p.startswith("xhr/formdata") and p not in [
        "xhr/formdata/append-formelement.html",
        "xhr/formdata/constructor-formelement.html",
        "xhr/formdata/constructor-submitter-coordinate.html",
        "xhr/formdata/constructor-submitter.html",
        "xhr/formdata/delete-formelement.html",
        "xhr/formdata/get-formelement.html",
        "xhr/formdata/has-formelement.html",
        "xhr/formdata/set-formelement.html"])


debug("\n".join(all_paths))
counter = Counter(
    "any" if path.endswith(".any.js")
    else "html" if path.endswith(".html")
    else "xhtml" if path.endswith(".xhtml")
    else "worker" if path.endswith(".worker.js")
    else "window" if path.endswith(".window.js")
    else path#.rsplit(".")[-1]
    for path in all_paths
)
debug(counter)
debug("Done")

tree = {}
for path in all_paths:
    debug(path)
    find_and_insert(tree, path.split("/"))
    debug(tree)
    debug(80 * "-")
debug(tree)
if outputpath == "-":
    print(tree)
else:
    with open(outputpath, "w") as fp:
        json.dump(tree, fp)
