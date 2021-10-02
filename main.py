import os
import pickle
import argparse

from fileinfo import FileInfo
from match_algorithm import MatchVideos, Interval


parser = argparse.ArgumentParser()

parser.add_argument("vSource", help="Source video file for the video")
parser.add_argument("aSource", help="Source video file for the audio")
#parser.add_argument("clean", help="Performs a clean run, discarding previous data if exists")

args = parser.parse_args()

# Genera good e bad in base ai parametri
good = FileInfo(args.vSource, needsFilters=True)
bad  = FileInfo(args.aSource, needsFilters=False)

main_folder = os.path.dirname(os.path.realpath(__file__))

k = 25

goodStart = 0
goodEnd = good.getScenesCount() - 1

badStart = 0
badEnd = bad.getScenesCount() - 1

mv = MatchVideos(bad, good)

matches, unmatchedIntervals = mv.findMatches(Interval(badStart, badEnd, goodStart, goodEnd), relax=0)


curRelax = 1
maxRelax = 7

relaxedMatches = [] 
while curRelax <= maxRelax and unmatchedIntervals:
    curRelaxedMatches = []
    relaxedUnmatchedIntervals = []
    
    for interval in unmatchedIntervals:
        matchesR, unmatchedIntervalsR = mv.findMatches(interval, relax=curRelax)
        
        if matchesR:
            curRelaxedMatches += matchesR
        
        if unmatchedIntervalsR:
            relaxedUnmatchedIntervals += unmatchedIntervalsR

    relaxedMatches += curRelaxedMatches
    unmatchedIntervals = relaxedUnmatchedIntervals
    
    curRelax += 1


def removeOverlappingMatches(arr):
    arr = list(sorted(arr))
    newArr = []
    
    i = 0
    while i < len(arr):
        m = arr[i]
        if i + 1 < len(arr):
            if m.overlaps(arr[i + 1]):
                print(f"{m} overlaps {arr[i + 1]}")
                
                if m.contains(arr[i + 1]):
                    print(f"    {m} contains {arr[i + 1]}")
                    newArr.append(m)
                    i += 1
                elif arr[i + 1].contains(m):
                    print(f"    {arr[i + 1]} contains {m}")
                else:
                    print("    There isn't one perfectly contained in the other one")
                    raise BaseException("This shouldn't be happening")
            else:
                newArr.append(m)
        else:
            newArr.append(m)
        
        i += 1
    return newArr

print("FINAL MATCHES!!!")
print(matches)

matches = list(sorted(matches))
relaxedMatches = list(sorted(relaxedMatches))

with open('unrelaxed_matches.pkl', 'wb') as f:
    pickle.dump(matches, f, pickle.HIGHEST_PROTOCOL)

with open('relaxed_matches.pkl', 'wb') as f:
    pickle.dump(relaxedMatches, f, pickle.HIGHEST_PROTOCOL)

print(f"Safe [unrelaxed] matches: {matches}")
print(f"Unsafe [relaxed] matches: {relaxedMatches}")
print(f"Still unmatched Intervals: {unmatchedIntervals}")

matches = removeOverlappingMatches(matches)
relaxedMatches = removeOverlappingMatches(relaxedMatches)

print(f"Safe [unrelaxed] matches: {matches}")
print(f"Unsafe [relaxed] matches: {relaxedMatches}")
print(f"Still unmatched Intervals: {unmatchedIntervals}")


matches += relaxedMatches
matches = removeOverlappingMatches(matches)

print(f"All matches: {matches}")

with open('final_matches.pkl', 'wb') as f:
    pickle.dump(matches, f, pickle.HIGHEST_PROTOCOL)