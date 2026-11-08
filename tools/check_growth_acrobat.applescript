-- Usage: osascript tools/check_growth_acrobat.applescript /absolute/example.pdf 8
-- Opens the PDF in desktop Acrobat Reader. Add a third argument "restart"
-- only for an explicit replay/performance test; the default does not restart.
-- This checks playback progress/stopping, not visual flicker or printing.
on run argv
  set pdfPath to item 1 of argv
  set playbackSeconds to (item 2 of argv) as real
  tell application "Adobe Acrobat Reader"
    activate
    open POSIX file pdfPath
    delay 2
    set initialInfo to do script "JSON.stringify({version:app.viewerVersion,path:this.path,bytes:this.filesize,page:this.pageNum,animations:typeof anim==='undefined'?null:Object.keys(anim)})"
    do script "var floralTestLabel=Object.keys(anim)[0];var floralTestTicks=0;if(typeof floralTestOriginalTick==='undefined'){floralTestOriginalTick=a0_gotoNext;}a0_gotoNext=function(){floralTestTicks++;floralTestOriginalTick();};'observing'"
    if (count of argv) > 2 then
      if item 3 of argv is "restart" then
        do script "anim[floralTestLabel].stopFirst();anim[floralTestLabel].playFwd();'restarted'"
      end if
    end if
    delay 1
    set firstInfo to do script "JSON.stringify({frame:anim[floralTestLabel].frameNum,ticks:floralTestTicks,fps:anim[floralTestLabel].fps,playing:anim[floralTestLabel].isPlaying})"
    delay playbackSeconds
    set lastInfo to do script "JSON.stringify({frame:anim[floralTestLabel].frameNum,ticks:floralTestTicks,frames:anim[floralTestLabel].numFrames,playing:anim[floralTestLabel].isPlaying})"
    return {initialInfo, firstInfo, lastInfo}
  end tell
end run
