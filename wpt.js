import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { exit } from 'node:process';

async function fetchText(url) {
  const response = await fetch(url);
  return await response.text();
}

async function runTest(runtimeSpec, content, url) {
  const tempFilePath = await Deno.makeTempFile();
  await Deno.writeTextFile(tempFilePath, content);
  const command = new Deno.Command(runtimeSpec.binary, {
    args: [tempFilePath],
    stderr: "piped",
    stdout: "piped",
  });

  const testProcess = command.spawn();
  const timeoutId = setTimeout(() => { try { testProcess.kill() } catch {} }, 1000);
  const { code, stdout, stderr } = await testProcess.output();
  clearTimeout(timeoutId);
  const stdoutT = new TextDecoder().decode(stdout);
  const results = stdoutT.split("\n").filter(line => line).map(line => {
    try { return JSON.parse(line) }
    catch (e) {
      // console.log(url)
      // console.log("------------------------------------------------")
      // console.log(stdoutT)
      // console.log("------------------------------------------------")
      // throw e;
      // Note that tests can run `console.log`
      return undefined;
    }
  }).filter(line => line);

  if (code === 0) {
    await Deno.remove(tempFilePath);
  }
  return {
    code,
    results,
    stderr: new TextDecoder().decode(stderr),
    path: tempFilePath,
  }
}

async function getRunInfo(runtimeSpec) {
  const { binary, product, browser_channel, os } = runtimeSpec;
  const command = new Deno.Command(binary, {
    args: ["--version"],
  });
  const { stdout } = await command.output();
  const version = new TextDecoder().decode(stdout).trim();
  return {
    product, browser_channel, os,
    browser_version: version,
    revision: process.env.WPT_REVISION || 'unknown',
  }
}

// https://github.com/web-platform-tests/wpt/blob/b24eedd/resources/testharness.js#L3705
function sanitizeUnpairedSurrogates(str) {
  return str.replace(
    /([\ud800-\udbff]+)(?![\udc00-\udfff])|(^|[^\ud800-\udbff])([\udc00-\udfff]+)/g,
    function(_, low, prefix, high) {
      let output = prefix || '';  // Prefix may be undefined
      const string = low || high;  // Only one of these alternates can match
      for (let i = 0; i < string.length; i++) {
        output += codeUnitStr(string[i]);
      }
      return output;
    });
}

function codeUnitStr(char) {
  return 'U+' + char.charCodeAt(0).toString(16);
}

class ReportResult {
  #startTime;

  constructor(name) {
    this.test = name;
    this.subtests = [];
    this.#startTime = Date.now();
  }

  // Map WPT test status to strings
  static getTestStatus(status) {
    switch (status) {
      case 1:
        return kFail;
      case 2:
        return kTimeout;
      case 3:
        return kIncomplete;
      case NODE_UNCAUGHT:
        return kUncaught;
      default:
        return kPass;
    }
  }

  /**
   * Report the status of each specific test case (there could be multiple
   * in one test file).
   * @param {Test} test The Test object returned by WPT harness
   */
  resultCallback(test) {
    const status = ReportResult.getTestStatus(test.status);
    if (status !== kPass) {
      this.fail(test);
    } else {
      this.succeed(test);
    }
  }

  succeed(test) {
    this.#addSubtest(test.name, 'PASS');
  }

  fail(test, message = '') {
    this.#addSubtest(test.name, 'FAIL', message);
  }

  #addSubtest(name, status, message) {
    const subtest = {
      status,
      // https://github.com/web-platform-tests/wpt/blob/b24eedd/resources/testharness.js#L3722
      name: sanitizeUnpairedSurrogates(name),
    };
    if (message) {
      // https://github.com/web-platform-tests/wpt/blob/b24eedd/resources/testharness.js#L4506
      subtest.message = sanitizeUnpairedSurrogates(message);
    }
    this.subtests.push(subtest);
  }

  finishWith(harnessStatus) {
    const status = ReportResult.getTestStatus(harnessStatus);

    // Treat it like a test case failure
    if (status === kTimeout) {
      // Mark the whole test as TIMEOUT in wpt.fyi report.
      this.finish('TIMEOUT');
    } else if (status !== kPass) {
      // Mark the whole test as ERROR in wpt.fyi report.
      this.finish('ERROR');
    } else {
      this.finish();
    }
  }

  finish(status = "OK") {
    this.status = status;
    this.duration = Date.now() - this.#startTime;
  }
}

// Generates a report that can be uploaded to wpt.fyi.
// Checkout https://github.com/web-platform-tests/wpt.fyi/tree/main/api#results-creation
// for more details.
class WPTReport {
  constructor() {
    this.filename = `wptreport.json`;
    /** @type {Map<string, ReportResult>} */
    this.results = new Map();
    this.time_start = Date.now();
  }

  /**
   * Get or create a ReportResult for a test spec.
   * @param {WPTTestSpec} spec
   * @returns {ReportResult}
   */
  getResult(spec) {
    const name = spec.filename;
    if (this.results.has(name)) {
      return this.results.get(name);
    }
    const result = new ReportResult(name);
    this.results.set(name, result);
    return result;
  }

  /**
   * @returns {void}
   */
  write(run_info) {
    this.time_end = Date.now();
    const results = Array.from(this.results.values())
    fs.writeFileSync(this.filename, JSON.stringify({
      time_start: this.time_start,
      time_end: this.time_end,
      run_info,
      results,
    }));
  }
}

// A specification of WPT test
class WPTTestSpec {
  /**
   * @param {string} filename path of the test, relative to the web-platform-tests root, e.g.
   *   '/html/webappapis/microtask-queuing/test.any.js', optionally with a variant
   */
  constructor(filename) {
    this.filename = filename;
    this.url = new URL(filename, "http://web-platform.test:8000");
  }

  /**
   * @returns {{ script?: string[]; [key: string]: string }} parsed META tags of a spec file
   */
  static getMeta(content) {
    const matches = content.match(/\/\/ META: .+/g);
    if (!matches) {
      return {};
    }
    const result = {};
    for (const match of matches) {
      const parts = match.match(/\/\/ META: ([^=]+?)=(.+)/);
      const key = parts[1];
      const value = parts[2];
      if (key === 'variant') {
        continue;
      }
      if (key === 'script') {
        if (result[key]) {
          result[key].push(value);
        } else {
          result[key] = [value];
        }
      } else {
        result[key] = value;
      }
    }
    return result;
  }
}

class StatusLoader {
  /**
   * @param {string} path relative path of the WPT subset
   */
  constructor(expectationsPath) {
    /** @type {WPTTestSpec[]} */
    this.specs = this.grep(expectationsPath).map(file => new WPTTestSpec(file));
  }

  grep2(path, tree, result) {
    for (const [k, v] of Object.entries(tree)) {
      let subpath = path + "/" + k;
      if (v === true) {
        if (!k.includes(".any.html")) {
          console.error(subpath); // FIXME
        } else {
          result.push(subpath.replace(".html", ".js")); /// FIXME fix input
        }
      } else {
        this.grep2(subpath, v, result);
      }
    }
  }

  /**
   * Build the list of tests from a tree-shaped JSON file
   * @param {string} expectationsPath
   * @returns {any[]}
   */
  grep(expectationsPath) {
    const tests = JSON.parse(fs.readFileSync(expectationsPath, 'utf8'));
    const result = [];
    this.grep2("", tests, result);
    return result;
  }
}

const kPass = 'pass';
const kFail = 'fail';
const kTimeout = 'timeout';
const kIncomplete = 'incomplete';
const kUncaught = 'uncaught';
const NODE_UNCAUGHT = 100;

const limit = (concurrency) => {
  let running = 0;
  const queue = [];

  const execute = async (fn) => {
    if (running < concurrency) {
      running++;
      try {
        await fn();
      } finally {
        running--;
        if (queue.length > 0) {
          execute(queue.shift());
        } else {
          exit(0)
        }
      }
    } else {
      queue.push(fn);
    }
  };

  return execute;
};

class WPTRunner {
  constructor(expectationsPath, { concurrency = os.availableParallelism() - 1 || 1 } = {}) {
    this.concurrency = concurrency;
    this.status = new StatusLoader(expectationsPath);
    this.specs = new Set(this.status.specs);
    this.inProgress = new Set();
    this.report = new WPTReport();
  }

  /**
   * @param {string} url
   * @param {string?} title
   * @param {string} harness
   * @returns {string}
   */
  static fullInitScript(url, title, harness) {
    let initScript = `
      function sanitizeUnpairedSurrogates(str) {
        return str.replace(
          /([\ud800-\udbff]+)(?![\udc00-\udfff])|(^|[^\ud800-\udbff])([\udc00-\udfff]+)/g,
          function(_, low, prefix, high) {
            let output = prefix || '';  // Prefix may be undefined
            const string = low || high;  // Only one of these alternates can match
            for (let i = 0; i < string.length; i++) {
              output += codeUnitStr(string[i]);
            }
            return output;
          });
      }

      function codeUnitStr(char) {
        return 'U+' + char.charCodeAt(0).toString(16);
      }

      globalThis.self = globalThis; //TODO: must be implemented per mca
      globalThis.location = new URL("${url}");
      globalThis.GLOBAL = {
        isWindow() { return false; },
        isShadowRealm() { return false; },
      };
    `;
    if (title) {
      initScript = `${initScript}\nglobalThis.META_TITLE = "${title}";`;
    }
    initScript += harness
    initScript += `
      add_result_callback((result) => {
        console.log(JSON.stringify({
          type: 'result',
          result: {
            status: result.status,
            name: result.name,
            message: result.message,
            stack: result.stack,
          },
        }));
      });
      add_completion_callback((_, status) => {
        console.log(JSON.stringify({
          type: 'completion',
          status,
        }));
      });
    `;

    return initScript;
  }

  static async getScript(spec, harness) {
    const testPath = spec.url;
    const content = await fetchText(testPath);
    const meta = WPTTestSpec.getMeta(content);

    const scriptsToRun = [
      { filename: "Init script", code: WPTRunner.fullInitScript(spec.url.href, meta.title, harness) }
    ];

    // Scripts specified with the `// META: script=` header
    if (meta.script) {
      const scripts = await Promise.all(meta.script.map(async (script) => {
        const path = new URL(script, testPath);
        const data = await fetchText(path);
        const obj = {
          code: data,
          filename: path.toString(),
        };
        return obj;
      }));
      scriptsToRun.push(...scripts);
    }
    // The actual test
    const obj = {
      code: content,
      filename: spec.url.toString(),
    };
    scriptsToRun.push(obj);
    const script = scriptsToRun.map(({code, filename}) => `// ${filename}\n${code}\n;`).join("\n");
    return script;
  }

  async runJsTests(runtimeSpec, runInfo) {
    const queue = this.buildQueue();

    const run = limit(this.concurrency);

    const harnessPath = "http://web-platform.test:8000/resources/testharness.js";
    const harness = await fetchText(harnessPath);
    for (const spec of queue) {
      run(async () => {
        const script = await WPTRunner.getScript(spec, harness);
        const reportResult = this.report?.getResult(spec);
        this.inProgress.add(spec);
        let { code, results, stderr, path } = await runTest(runtimeSpec, script, spec.url);
        if (code !== 0) {
          // Mark the whole test as failed in wpt.fyi report.
          reportResult?.finish('ERROR');
          this.inProgress.delete(spec);
          this.report?.write();
          return;
        }
        for (const result of results) {
          switch (result.type) {
            case 'result':
              reportResult?.resultCallback(result.result);
              break;
            case 'completion':
              reportResult?.finishWith(result.status.status);
              this.inProgress.delete(spec);
              // Write report incrementally so results survive even if the process
              // is killed before the exit handler runs.
              this.report?.write();
              break;
            default:
              throw new Error(`Unexpected message from worker: ${result.type}`);
          }
        }
        this.inProgress.delete(spec);
      });
    }

    process.on('exit', () => {
      console.log("on 'exit'")
      for (const spec of this.inProgress) {
        // Mark the whole test as failed in wpt.fyi report.
        const reportResult = this.report?.getResult(spec);
        reportResult?.finish('ERROR');
      }
      let failures = 0;
      for (const [_, item] of this.report.results) {
        if (item.status !== "OK" || item.subtests.some(s => s.status !== "PASS")) {
          failures++;
        }
      }

      // Write the report on clean exit. The report is also written
      // incrementally after each spec completes (see completionCallback)
      // so that results survive if the process is killed.
      this.report?.write(runInfo);

      const ran = queue.length;
      console.log('');
      console.log(`Ran ${ran} tests, ${ran - failures} passed, ${failures} failures`);
    });
  }

  /**
   * Report the status of each WPT test (one per file)
   * @param {WPTTestSpec} spec
   * @param {object} harnessStatus - The status object returned by WPT harness.
   * @param {ReportResult} reportResult The report result object
   */
  completionCallback(spec, harnessStatus, reportResult) {
    reportResult?.finishWith(harnessStatus.status);
    this.inProgress.delete(spec);
    // Write report incrementally so results survive even if the process
    // is killed before the exit handler runs.
    this.report?.write();
  }

  buildQueue() {
    const queue = [];
    let argFilename;
    let argVariant;
    if (process.argv[3]) {
      ([argFilename, argVariant = ''] = process.argv[3].split('?'));
    }
    for (const spec of this.specs) {
      if (!argFilename) {
        queue.push(spec);
        continue;
      }
      let [filename, variant = ''] = spec.filename.split('?');
      if (filename === argFilename && (!argVariant || variant === argVariant)) {
        queue.push(spec);
      }
    }

    // If the tests argument is `subset.any.js`, only `subset.any.js` (all variants) will be run.
    // If it is 'subset.any.js?1-10'`, only the `?1-10` variant of `subset.any.js` will be run.
    if (argFilename && queue.length === 0) {
      throw new Error(`${process.argv[3]} not found!`);
    }

    return queue;
  }
}

const runtimeSpec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const runInfo = await getRunInfo(runtimeSpec);

const runner = new WPTRunner(path.join(import.meta.dirname, 'expectation.json'));
runner.runJsTests(runtimeSpec, runInfo);
