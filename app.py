import os, re, json, shutil, subprocess, tempfile, random
from pathlib import Path
import numpy as np
import gradio as gr

FFMPEG = shutil.which('ffmpeg')
FFPROBE = shutil.which('ffprobe')

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-1800:])
    return p.stdout

def duration(path):
    info=json.loads(run([FFPROBE,'-v','error','-show_entries','format=duration','-of','json',str(path)]))
    return float(info['format']['duration'])

def plan(prompt):
    s=prompt.lower()
    slow=bool(re.search(r'slow|cinematic|dramatic',s))
    transition=bool(re.search(r'smooth|fade|transition',s))
    rapid=bool(re.search(r'fast|quick|rapid|every beat',s))
    return slow,transition,rapid

def beats_from_music(path, max_length):
    import librosa
    y,sr=librosa.load(path,sr=11025,mono=True,duration=min(max_length+5,95))
    _,frames=librosa.beat.beat_track(y=y,sr=sr,hop_length=256,trim=False)
    times=librosa.frames_to_time(frames,sr=sr,hop_length=256)
    return [float(x) for x in times if 0.2 < x < max_length]

def edit(videos,music,prompt,length,progress=gr.Progress()):
    if not FFMPEG or not FFPROBE:
        raise gr.Error('FFmpeg and FFprobe must be installed and available on PATH.')
    if not videos:
        raise gr.Error('Upload at least one video.')
    paths=[Path(x) for x in videos]
    slow,transition,rapid=plan(prompt)
    work=Path(tempfile.mkdtemp(prefix='ai_edit_'))
    try:
        progress(0.05,desc='Analyzing videos')
        durations=[duration(x) for x in paths]
        valid=[(p,d) for p,d in zip(paths,durations) if d>0.35]
        if not valid: raise gr.Error('Videos are too short.')
        target=float(length)
        beat_times=[]
        if music:
            progress(0.15,desc='Detecting music beats')
            try: beat_times=beats_from_music(music,target)
            except Exception as e: raise gr.Error('Could not analyze music: '+str(e))
        # Use beat positions as cut boundaries, with a minimum clip duration.
        boundaries=[0.0]
        if beat_times:
            for t in beat_times:
                if t-boundaries[-1]>= (0.48 if rapid else 0.85) and target-t>0.3:
                    boundaries.append(t)
        if len(boundaries)<2:
            step=1.4 if rapid else 2.5
            boundaries=list(np.arange(0,target,step))
            if not boundaries: boundaries=[0.0]
        boundaries.append(target)
        # Limit clips for reasonable processing time.
        if len(boundaries)>65:
            stride=int(np.ceil((len(boundaries)-1)/64))
            boundaries=boundaries[::stride]
            if boundaries[-1]!=target: boundaries.append(target)
        segments=[]
        for i,(start,end) in enumerate(zip(boundaries[:-1],boundaries[1:])):
            length_out=end-start
            source,source_duration=valid[i%len(valid)]
            # Alternate normal and half-speed highlights when slow motion requested.
            speed=0.5 if slow and i%4==2 else 1.0
            required=length_out*speed
            if required>source_duration-0.1:
                speed=min(speed,max(0.2,(source_duration-0.12)/length_out))
                required=length_out*speed
            offset=max(0,(source_duration-required)*((i*0.37)%1))
            fade=min(0.12,length_out/7) if transition else 0
            filters=f'setpts=(PTS-STARTPTS)/{speed},fps=30,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p'
            if fade:
                filters+=f',fade=t=in:st=0:d={fade:.3f},fade=t=out:st={max(0,length_out-fade):.3f}:d={fade:.3f}'
            seg=work/f'clip_{i:03d}.mp4'
            progress(0.2+0.65*(i/max(1,len(boundaries)-1)),desc=f'Rendering clip {i+1}/{len(boundaries)-1}')
            run([FFMPEG,'-y','-hide_banner','-loglevel','error','-ss',f'{offset:.4f}','-t',f'{required:.4f}','-i',str(source),'-vf',filters,'-t',f'{length_out:.4f}','-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',str(seg)])
            segments.append(seg)
        concat=work/'list.txt'
        concat.write_text(''.join("file '"+str(p).replace("'","'\\''")+"'\n" for p in segments))
        joined=work/'joined.mp4'
        run([FFMPEG,'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(joined)])
        output=work/'football_edit.mp4'
        if music:
            run([FFMPEG,'-y','-hide_banner','-loglevel','error','-i',str(joined),'-stream_loop','-1','-i',str(music),'-map','0:v:0','-map','1:a:0','-t',str(target),'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)])
        else:
            shutil.copy2(joined,output)
        # Persistent result outside the temporary work folder for Gradio serving.
        final=Path(tempfile.mkdtemp(prefix='ai_edit_result_'))/'football_edit.mp4'
        shutil.copy2(output,final)
        progress(1,desc='Done')
        summary=f'Finished! {len(segments)} cuts; beat sync: {"music detected" if music and beat_times else "timed cuts"}; slow motion: {"on" if slow else "off"}; smooth fades: {"on" if transition else "off"}. Export: 1280×720, MP4.'
        return str(final),str(final),summary
    finally:
        shutil.rmtree(work,ignore_errors=True)

with gr.Blocks(title='AI Edit Studio',theme=gr.themes.Soft(primary_hue='violet')) as demo:
    gr.Markdown('# ⚽ AI Edit Studio\nUpload football clips, add music, tell the editor what you want, and export your video.')
    with gr.Row():
        with gr.Column():
            videos=gr.File(label='Upload football videos',file_count='multiple',file_types=['video'],type='filepath')
            music=gr.Audio(label='Upload music (optional, enables beat sync)',type='filepath',sources=['upload'])
            prompt=gr.Textbox(label='Tell the AI how to edit',lines=4,value='Make a cool football edit, cut on every beat, add slow motion and smooth transitions.')
            length=gr.Slider(5,60,value=20,step=1,label='Edit length (seconds)')
            go=gr.Button('✨ Create my edit',variant='primary')
        with gr.Column():
            preview=gr.Video(label='Finished video')
            download=gr.File(label='Download MP4')
            status=gr.Textbox(label='Editor status',interactive=False)
    go.click(edit,[videos,music,prompt,length],[preview,download,status])
    gr.Markdown('**Note:** This first version uses prompt-based editing rules rather than a generative AI model. Beat timing is automatic; clip selection is sequential rather than action-aware. Only upload footage and music you have permission to use.')

if __name__=='__main__':
    demo.launch(server_name="0.0.0.0", server_port=7860, allowed_paths=[tempfile.gettempdir()])
