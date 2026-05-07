import logger from "../misc/logger";
import {mapGetSet, locationToStringWithFileAndEnd, Location, SimpleLocation} from "../misc/util";
import {
    //AbbreviatedPathPattern,
    AccessPathPattern,
    CallResultAccessPathPattern,
    ComponentAccessPathPattern,
    ImportAccessPathPattern,
    PropertyAccessPathPattern
} from "./patterns";
import {isCallExpression, isNewExpression, isOptionalCallExpression, Node} from "@babel/types";
import {AccessPathPatternCanonicalizer} from "./patternparser";
import {AccessPath} from "../analysis/accesspaths";
import {FragmentState} from "../analysis/fragmentstate";

export type PatternType = "import" | "read" | "write" | "call" | "component";

export type AccessPathPatternToNodes = Record<PatternType, Map<AccessPathPattern, Set<Node>>>;
export type NodeToAccessPathPatterns = Record<PatternType, Map<Node, Set<AccessPathPattern>>>;
export type AccessPathString = string;
export type AccessPathPatternToLocations = Record<PatternType, Record<AccessPathString, Array<SimpleLocation & {filename: string}>>>;


//DEBUG
// Map που συνδέει το ID του Node με μια λίστα από callers
//const nodeToCallers = new Map<number, Array<{name: string, loc: string}>>();


/**
 * Finds the usage of the API of external modules.
 */
export function getAPIUsage(f: FragmentState): [AccessPathPatternToNodes, NodeToAccessPathPatterns] {
    logger.info("Collecting API usage");
    const reached: AccessPathPatternToNodes = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const res1: AccessPathPatternToNodes = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const res2: NodeToAccessPathPatterns = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const c = new AccessPathPatternCanonicalizer;
    const worklist = new Map<AccessPathPattern, Set<AccessPath>>();

    function add(t: PatternType, p: AccessPathPattern, ap: AccessPath, n: Node) {
        // Καθαρισμός του pattern μέσω του canonicalizer (χωρίς abbreviations)
        p = c.canonicalize(p);
        
        const aps = mapGetSet(reached[t], p);
        if (!aps.has(n)) {
            if (logger.isDebugEnabled())
                logger.debug(`Found ${t} ${p} at ${locationToStringWithFileAndEnd(n.loc)}`);
            aps.add(n);

            function isReadAtCall(): boolean {
                if (t === "read") {
                    const m = f.callResultAccessPaths.get(ap);
                    if (m)
                        for (const f of m.keys())
                            if ((isCallExpression(f) || isOptionalCallExpression(f) || isNewExpression(f)) && f.callee === n)
                                return true;
                }
                return false;
            }

            if (isReadAtCall()) { 
                if (logger.isDebugEnabled())
                    logger.debug(`Read-call ${ap} at ${locationToStringWithFileAndEnd(n.loc)}`);
            } else {
                mapGetSet(res1[t], p).add(n);
                mapGetSet(res2[t], n).add(p);
            }
            mapGetSet(worklist, p).add(ap);
        }
    } // κλείνει σωστά η add

    // find imports
    for (const [ap, m] of f.moduleAccessPaths)
        for (const n of m.keys())
            add("import", c.canonicalize(new ImportAccessPathPattern(ap.moduleInfo.getOfficialName())), ap, n);

    // iteratively find property reads, writes, calls and components
    for (const [p, aps] of worklist)
        for (const ap of aps) {
            aps.delete(ap);
            if (aps.size === 0)
                worklist.delete(p);
            
            // property reads
            const m1 = f.propertyReadAccessPaths.get(ap);
            if (m1)
                for (const [prop, np] of m1)
                    for (const [n2, {bp}] of np)
                        add("read", c.canonicalize(new PropertyAccessPathPattern(p, [prop])), bp, n2);
            
            // property writes
            const m2 = f.propertyWriteAccessPaths.get(ap);
            if (m2)
                for (const [prop, np] of m2)
                    for (const [n2, {bp}] of np)
                        add("write", c.canonicalize(new PropertyAccessPathPattern(p, [prop])), bp, n2);

            // calls
            const m3 = f.callResultAccessPaths.get(ap);
            if (m3)
                for (const [n2, {bp}] of m3)
                    add("call", c.canonicalize(new CallResultAccessPathPattern(p)), bp, n2);

            // components
            const m4 = f.componentAccessPaths.get(ap);
            if (m4)
                for (const [n2, {bp}] of m4)
                    add("component", c.canonicalize(new ComponentAccessPathPattern(p)), bp, n2);
        }

    return [res1, res2];
}

export function reportAPIUsage(r1: AccessPathPatternToNodes, r2: NodeToAccessPathPatterns) { // TODO: split into two functions?
    logger.info("API usage, access path patterns -> nodes:");
    let numAccessPathPatterns = 0, numAccessPathPatternsAtNodes = 0;
    for (const [t, m] of Object.entries(r1)) {
        for (const [p, ns] of m) {
            logger.info(`${t} ${p}:`);
            for (const n of ns)
                logger.info(`  ${locationToStringWithFileAndEnd(n.loc)}`);
            numAccessPathPatternsAtNodes += ns.size;
        }
        numAccessPathPatterns += m.size;
    }
    // logger.info("API usage, nodes -> access path patterns:"); // TODO: remove this part, also in getAPIUsage?
    // for (const [t, m] of Object.entries(r2))
    //     for (const [n, ps] of m) {
    //         logger.info(`${locationToStringWithFileAndEnd(n.loc)}:`);
    //         for (const p of ps)
    //             logger.info(`  ${t} ${p}`);
    //     }
    logger.info(`Access path patterns: ${numAccessPathPatterns}, access path patterns at nodes: ${numAccessPathPatternsAtNodes}`);
}

//DEBUG
//export function convertAPIUsageToJSON(r: AccessPathPatternToNodes): AccessPathPatternToLocations {
  //  const res: AccessPathPatternToLocations = {import: {}, read: {}, write: {}, call: {}, component: {}};
    //for (const type of Object.getOwnPropertyNames(r) as Array<PatternType>) {
      //  const t: Record<AccessPathString, Array<SimpleLocation & {filename: string}>> = {};
        //for (const [p, nodes] of r[type]) {
          //  const a: Array<SimpleLocation & {filename: string}> = [];
            //for (const n of nodes)
              //  if (n.loc) {
                //    const loc = n.loc as Location;
                  //  if (loc.module)
                    //    a.push({filename: loc.module.getPath(), start: loc.start, end: loc.end});
                //}
//            t[p.toString()] = a;
  //      }
    //    res[type] = t;
//    }
  //  return res;
//}

// Εισαγωγή του Reporter στην αρχή του αρχείου αν δεν υπάρχει
//import {AnalysisStateReporter} from "../output/analysisstatereporter";

export function convertAPIUsageToJSON(r: AccessPathPatternToNodes, _?: any, f?: any): any {
    const res: any = {import: {}, read: {}, write: {}, call: {}, component: {}};
    
    for (const type of Object.getOwnPropertyNames(r) as Array<PatternType>) {
        const t: Record<string, any> = {};
        for (const [p, nodes] of r[type]) {
            const a: Array<any> = [];
            // Χρησιμοποιούμε Set για να κρατάμε μοναδικά locations ΑΝΑ pattern
            const seenAtPattern = new Set<string>(); 

            for (const n of nodes) {
                if (n.loc) {
                    const loc = n.loc as Location;
                    const locKey = locationToStringWithFileAndEnd(n.loc);
                    
                    // Δημιουργία κλειδιού για να δούμε αν έχουμε ξαναβάλει αυτή τη γραμμή
                    const dedupeKey = `${loc.module?.getPath()}:${loc.start.line}:${loc.start.column}`;

                    if (!seenAtPattern.has(dedupeKey)) {
                        seenAtPattern.add(dedupeKey);
                        
                        const nodeInfo: any = {
                            filename: loc.module?.getPath(),
                            start: loc.start,
                            end: loc.end,
                            // Deduplication και στους callers
                            callers: deduplicateCallers(f ? (f.nodeToCallers.get(locKey as any) || []) : [])
                        };
                        a.push(nodeInfo);
                    }
                }
            }
            t[p.toString()] = a;
        }
        res[type] = t;
    }
    return res;
}

// Βοηθητική συνάρτηση για να καθαρίσει τους callers βάσει ΜΟΝΟ του Loc
function deduplicateCallers(callers: any[]): any[] {
    const seenLocs = new Set();
    return callers.filter(c => {
        // Χρησιμοποιούμε μόνο το c.loc ως κλειδί μοναδικότητας
        const key = c.loc; 
        if (seenLocs.has(key)) return false;
        seenLocs.add(key);
        return true;
    });
}