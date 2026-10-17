(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = {search:'', letter:'', sort:'name', type:'', section:'', missing:false, offset:0, total:0, stats:{}, tokenSet:false, admin:true, loaded:false, timer:null, actorGeneration:0, actorAbort:null, actorLoading:false, actorKeys:new Set(),linkMode:'remote',plexLinkBase:'https://app.plex.tv/desktop/',artRevision:0};
  const alphabet = ['ALL',...'ABCDEFGHIJKLMNOPQRSTUVWXYZ','#'];
  const formatNumber = n => Number(n || 0).toLocaleString();
  const q = (selector, root = document) => root.querySelector(selector);
  const elt = (tag, cls, text) => { const node=document.createElement(tag); if(cls) node.className=cls; if(text !== undefined) node.textContent=text; return node; };
  const initials = name => name.split(/\s+/).map(p=>p[0]||'').slice(0,2).join('').toUpperCase();
  const imageOrInitials = (url, label, cls) => {
    const wrap=elt('div',cls);
    const fallback=elt('span','initials',initials(label));
    wrap.append(fallback);
    if(url){ const img=document.createElement('img');img.loading='lazy';img.alt=label;img.addEventListener('load',()=>{fallback.hidden=true});img.addEventListener('error',()=>{img.remove();fallback.hidden=false});img.src=url;wrap.append(img); }
    return wrap;
  };
  async function api(path, options){ const response=await fetch(path,options); let data;try{data=await response.json()}catch{data={error:'Unexpected server response'}} if(!response.ok)throw new Error(data.error||'Request failed');return data; }
  async function post(path,data){return api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
  function notify(message){const el=$('toast');el.textContent=message;el.hidden=false;setTimeout(()=>{if(el.textContent===message)el.hidden=true},4200)}
  function modal(id,open){$(id).hidden=!open;document.body.style.overflow=(!$('settingsOverlay').hidden||!$('actorOverlay').hidden||!$('reviewOverlay').hidden)?'hidden':'';}
  async function openSettings(){
    if(!state.admin){notify('To change Plex settings, open Cast Explorer on the server at http://127.0.0.1:8765');return;}
    try{const conf=await api('/api/config');$('plexUrl').value=conf.url;$('plexToken').value='';$('plexToken').placeholder=conf.token_set?'Already configured — leave blank to keep':'Paste your Plex authentication token';$('settingsError').textContent='';try{const a=await api('/api/art/config');$('artSettingsStatus').textContent='TMDB: '+(a.tmdb_enabled?'enabled':(a.tmdb_set?'token saved; enable via installer':'not configured'))+' · ThePornDB: '+(a.theporndb_set?'configured':'not configured')+' · Wikimedia: disabled';}catch(e){$('artSettingsStatus').textContent=e.message}modal('settingsOverlay',true);$('plexUrl').focus();void refreshEnrichment(true);}catch(e){notify(e.message)}
  }
  function buildAlphabet(){const bar=$('alphabet');bar.replaceChildren();for(const letter of alphabet){const btn=elt('button','alpha'+((state.letter||'ALL')===letter?' active':''),letter);btn.addEventListener('click',()=>{state.letter=letter==='ALL'?'':letter;buildAlphabet();loadActors(false);});bar.append(btn)}}
  function renderLibraries(){const nav=$('libraryNav');nav.replaceChildren();if(!state.stats.sections?.length){nav.append(elt('div','nav-muted','Your libraries will appear after the first index.'));return;}
    const all=elt('button','nav-button'+(!state.section?' active':''),'All libraries');all.addEventListener('click',()=>selectLibrary(''));nav.append(all);
    for(const library of state.stats.sections){const button=elt('button','nav-button'+(state.section===library.key?' active':''),library.name);button.title=library.name+' · '+library.count+' titles';button.addEventListener('click',()=>selectLibrary(library.key));nav.append(button)}
  }
  function selectLibrary(section){state.section=section;renderLibraries();loadActors(false);}
  function renderMediaNav(){for(const btn of document.querySelectorAll('[data-type]')){btn.classList.toggle('active',btn.dataset.type===state.type)}}
  function updateHeading(){let name='All performers';if(state.type==='movie')name='Movie performers';if(state.type==='show')name='TV performers';if(state.section){const section=state.stats.sections?.find(i=>i.key===state.section);if(section)name=section.name+' cast';}$('directoryHeading').textContent=name;}
  async function loadStats(){state.stats=await api('/api/stats');$('statPeople').textContent=formatNumber(state.stats.actors);$('statTitles').textContent=formatNumber(state.stats.titles);$('statCredits').textContent=formatNumber(state.stats.credits);renderLibraries();updateHeading();}
  async function loadActors(append=false){
    // Each change to search, sort, or filters begins a fresh result generation.
    // An older HTTP response must NEVER append cards to a newer result set.
    if(!append){
      state.actorGeneration++;
      if(state.actorAbort)state.actorAbort.abort();
      state.offset=0;
      state.actorKeys=new Set();
      $('actorGrid').replaceChildren();
    }else if(state.actorLoading){
      // Ignore repeated "Load more" clicks until the preceding page is complete.
      return;
    }
    updateHeading();
    const generation=state.actorGeneration;
    const requestedOffset=state.offset;
    const controller=new AbortController();
    state.actorAbort=controller;
    state.actorLoading=true;
    $('loadMore').disabled=true;
    const query=new URLSearchParams({search:state.search,section:state.section,type:state.type,letter:state.letter,sort:state.sort,missing:state.missing?'1':'0',limit:'72',offset:String(requestedOffset)});
    try{
      const data=await api('/api/actors?'+query,{signal:controller.signal});
      if(generation!==state.actorGeneration||controller.signal.aborted||requestedOffset!==state.offset)return;
      state.total=data.total;
      state.loaded=true;
      const fragment=document.createDocumentFragment();
      for(const actor of data.results){
        // Extra defense if a page includes a repeated cast entry.
        if(state.actorKeys.has(actor.key))continue;
        state.actorKeys.add(actor.key);
        const card=elt('button','actor-card');
        card.dataset.actorKey=actor.key;
        card.title='Explore '+actor.name;
        card.append(imageOrInitials(actor.image ? actor.image+'&v='+state.artRevision : '',actor.name,'actor-photo'));
        const info=elt('div','actor-info');
        const strong=elt('strong','',actor.name);
        const count=elt('span','',formatNumber(actor.appearance_count)+' '+(actor.appearance_count===1?'title':'titles'));
        info.append(strong,count);
        card.append(info);
        card.addEventListener('click',()=>openActor(actor.key));
        fragment.append(card);
      }
      $('actorGrid').append(fragment);
      // Offset reflects the number of API rows returned, not the number of unique cards.
      state.offset=requestedOffset+data.results.length;
      $('resultCount').textContent=formatNumber(data.total)+' '+(data.total===1?'performer':'performers');
      $('loadMore').hidden=state.offset>=data.total;
      const noData=!data.total;
      const firstScan=!(state.stats.actors||0) && !state.tokenSet;
      $('emptyState').hidden=!noData;
      $('emptyTitle').textContent=firstScan?'Your directory starts here':(state.stats.actors===0?'No performers indexed yet':'No matching performers');
      $('emptyText').textContent=firstScan?(state.admin?'Connect your Plex server and index all your libraries to build a cast directory.':'Plex connection must be configured on the server computer.'):(state.stats.actors===0?'Choose Sync library to import your movie and TV cast.':'Try changing the filters or searching a different name.');
      $('emptyAction').hidden=!firstScan||!state.admin;
    }catch(e){
      if(e.name!=='AbortError'&&generation===state.actorGeneration)notify('Could not load performers: '+e.message);
    }finally{
      if(state.actorAbort===controller){
        state.actorAbort=null;
        state.actorLoading=false;
        $('loadMore').disabled=false;
      }
    }
  }
  // The server uses the connecting client's actual socket address to decide if
  // local Plex is reachable. Off-LAN visitors use the original hosted Plex URL.
  // No Plex authentication token is ever inserted into the browser URL.
  function plexLink(key){
    const base=state.plexLinkBase;
    const id=state.stats.machine_id;
    if(!id)return base;
    return base+'#!/server/'+encodeURIComponent(id)+'/details?key='+encodeURIComponent('/library/metadata/'+key);
  }
  async function getPlexLinkMode(){
    try{const config=await api('/api/links');state.linkMode=config.mode;state.plexLinkBase=config.base;}
    catch{state.linkMode='remote';state.plexLinkBase='https://app.plex.tv/desktop/';}
  }
  let lastReviewTotal = -1;
  async function refreshEnrichment(forceReview=false){
    if(!state.admin || $('settingsOverlay').hidden)return;
    try{
      const result=await api('/api/enrich/status');
      const summary=[result.phase+': '+formatNumber(result.checked)+' / '+formatNumber(result.total)+' in this run',
        formatNumber(result.db_auto||0)+' automatically applied',
        formatNumber(result.review_waiting||0)+' waiting for review',
        formatNumber(result.db_unmatched||0)+' unmatched',
        formatNumber(result.remaining||0)+' not yet scanned'];
      $('enrichSummary').textContent=summary.join(' · ')+(result.last_error?' · Latest warning: '+result.last_error:'');
      $('enrichProgress').style.width=(result.total?Math.round(100*result.checked/result.total):0)+'%';
      const batch=result.single_batch||{};
      $('enrichAcceptUnique').disabled=!!batch.running;
      $('enrichAcceptUnique').textContent=batch.running?'Applying one-result portraits…':'Auto-accept queued single matches';
      $('enrichBatchSummary').hidden=!(batch.running||batch.checked||batch.failed);
      $('enrichBatchSummary').textContent='Single-result queue: '+formatNumber(batch.checked||0)+' / '+formatNumber(batch.total||0)+' checked · '+formatNumber(batch.applied||0)+' applied · '+formatNumber(batch.skipped||0)+' retained for review'+(batch.failed?' · '+batch.failed+' download errors':'')+(batch.last_error?' · '+batch.last_error:'');
      $('enrichStart').disabled=result.running;
      $('enrichPause').disabled=!result.running;
      $('enrichReviewCount').textContent=formatNumber(result.review_waiting||0)+' awaiting review (showing the newest 12).';
      if(forceReview || lastReviewTotal!==result.review_waiting){
        lastReviewTotal=result.review_waiting;
        const reviews=await api('/api/enrich/review');renderEnrichmentReviews(reviews.results||[]);
      }
    }catch(e){$('enrichSummary').textContent='Could not load enrichment status: '+e.message;}
  }
  function readablePlexTitle(item){
    const year = item.year ? ' ('+item.year+')' : '';
    return item.title + year;
  }
  function evidenceTag(choice){
    const n=(choice.matches||[]).length;
    const dated=(choice.matches||[]).filter(m=>m.year_verified).length;
    if((choice.matches||[]).some(m=>m.role_conflict))return ['caution','Conflicting credited roles — investigate before approving'];
    if(n>=2 && dated>=1)return ['corroborated','Multiple matching credits; confirm the identity'];
    if(n===1)return ['caution','Only one matching title — identity not confirmed'];
    return ['caution','Limited credit evidence — review carefully'];
  }
  function plexTitlesList(person, limit=12){
    const box=elt('div','verification-credits');
    const full=(person.plex_titles||[]);
    if(!full.length){box.append(elt('p','note','No Plex credits available.'));return box;}
    for(const title of full.slice(0,limit)){
      const item=elt('div','verification-credit');
      const main=elt('strong','',readablePlexTitle(title));
      const parts=[title.library||title.media_type];
      if(title.character)parts.push('Role: '+title.character);
      item.append(main,elt('small','',parts.filter(Boolean).join(' · ')));
      if(title.key){const a=elt('a','','Open in Plex ↗');a.href=plexLink(title.key);a.target='_blank';a.rel='noopener noreferrer';item.append(a);}
      box.append(item);
    }
    if(person.plex_title_count>full.length)box.append(elt('p','note','Showing '+full.length+' of '+person.plex_title_count+' Plex credits.'));
    return box;
  }
  function openPortraitReview(person, choice, index){
    const body=$('reviewBody');body.replaceChildren();
    $('reviewTitle').textContent='Verify portrait: '+person.name;
    const mode=evidenceTag(choice);
    const summary=elt('p','verification-alert '+mode[0],mode[1]);body.append(summary);
    const columns=elt('div','verification-columns');
    const left=elt('section','verification-plex');
    left.append(elt('h3','','Your Plex filmography'),elt('p','verification-muted',person.plex_title_count+' indexed '+(person.plex_title_count===1?'title':'titles')+' across your libraries'));
    left.append(plexTitlesList(person,30));
    const right=elt('section','verification-source');
    right.append(elt('h3','','Proposed portrait · '+choice.source));
    const picture=imageOrInitials(choice.preview,choice.name||person.name,'verification-image');right.append(picture);
    const fullImage=elt('a','verification-raw','Open full image ↗');fullImage.href=choice.preview;fullImage.target='_blank';fullImage.rel='noopener noreferrer';right.append(fullImage);
    right.append(elt('p','verification-muted','Provider lists this person as: '+(choice.name||person.name)));
    const provider=elt('a','verification-provider','Open original '+choice.source+' record ↗');
    provider.href=choice.reference;provider.target='_blank';provider.rel='noopener noreferrer';right.append(provider);
    const heading=elt('h4','','Matching production credits');right.append(heading);
    const matches=(choice.matches||[]);
    if(!matches.length)right.append(elt('p','verification-muted','No matching credits were recorded. Do not approve without independent verification.'));
    for(const credit of matches){
      const entry=elt('div','verification-match');
      entry.append(elt('strong','',credit.title));
      const yr=credit.year||'unknown';const src=credit.external_year||'unknown';
      entry.append(elt('small','',`Plex: ${yr} · ${choice.source}: ${src}`));
      if(credit.plex_character || credit.provider_character)entry.append(elt('small','',`Plex role: ${credit.plex_character||'not listed'} · Provider role: ${credit.provider_character||'not listed'}`));
      if(credit.role_conflict)entry.append(elt('span','unverified-year','Role mismatch: verify identity'));
      entry.append(elt('span',credit.year_verified?'verified-year':'unverified-year',credit.year_verified?'Year agrees':'Year not independently verified'));
      right.append(entry);
    }
    const extra=choice.other_titles||[];
    if(extra.length){
      right.append(elt('h4','','Other credits on provider'));
      const list=elt('div','verification-other',extra.map(c=>c.title+(c.year?' ('+c.year+')':'')).join(' · '));
      right.append(list);
    }else{
      right.append(elt('p','verification-muted','For additional provider credits, open the original record. Older scans may not include them.'));
    }
    columns.append(left,right);body.append(columns);
    const footer=elt('div','verification-actions');
    const confirm=elt('label','verification-confirm');
    const tick=document.createElement('input');tick.type='checkbox';
    confirm.append(tick,elt('span','','I checked that this photo belongs to the performer in my Plex library.'));
    footer.append(confirm);
    const controls=elt('div','verification-buttons');
    const reject=elt('button','secondary-button','Not this person');
    reject.addEventListener('click',async()=>{
      reject.disabled=true;
      try{await post('/api/enrich/reject',{key:person.key,i:index});modal('reviewOverlay',false);notify('Candidate rejected. No portrait was applied.');await refreshEnrichment(true);}
      catch(e){notify('Could not reject: '+e.message);reject.disabled=false;}
    });
    const cancel=elt('button','secondary-button','Return to queue');cancel.addEventListener('click',()=>modal('reviewOverlay',false));
    const approve=elt('button','primary-button','Save verified portrait');approve.disabled=true;
    tick.addEventListener('change',()=>approve.disabled=!tick.checked);
    approve.addEventListener('click',async()=>{
      if(!tick.checked)return;
      approve.disabled=true;
      try{await post('/api/enrich/approve',{key:person.key,i:index});modal('reviewOverlay',false);notify('Portrait saved for '+person.name);state.artRevision=Date.now();await refreshEnrichment(true);await loadActors(false);}
      catch(e){notify('Approval failed: '+e.message);approve.disabled=false;}
    });
    controls.append(reject,cancel,approve);footer.append(controls);body.append(footer);
    modal('reviewOverlay',true);
  }
  async function quickApproveSingle(person,button){
    button.disabled=true;
    try{
      await post('/api/enrich/approve',{key:person.key,i:0});
      notify('Portrait saved for '+person.name);
      state.artRevision=Date.now();
      await refreshEnrichment(true);await loadActors(false);
    }catch(e){notify('Approval failed: '+e.message);button.disabled=false;}
  }
  function renderEnrichmentReviews(people){
    const host=$('enrichReviewList');host.replaceChildren();
    if(!people.length){host.append(elt('p','note','No portraits currently need review.'));return;}
    for(const person of people){
      const wrap=elt('section','enrich-person');
      const head=elt('div','enrich-review-head');head.append(elt('h4','',person.name));
      head.append(elt('span','verification-muted',person.plex_title_count+' Plex '+(person.plex_title_count===1?'credit':'credits')));
      wrap.append(head);
      const summary=elt('div','enrich-plex-context');
      const titles=(person.plex_titles||[]).slice(0,6).map(c=>readablePlexTitle(c));
      summary.append(elt('strong','','Plex titles for comparison: '));
      summary.append(elt('span','',titles.join(' · ')+(person.plex_title_count>6?' · …':'')));
      wrap.append(summary);
      const grid=elt('div','enrich-candidates');
      person.choices.forEach((choice,i)=>{
        const tile=elt('div','enrich-candidate');
        const photo=imageOrInitials(choice.preview,choice.name||person.name,'enrich-photo');tile.append(photo);
        tile.append(elt('strong','','Candidate '+(i+1)+' · '+choice.source));
        const status=evidenceTag(choice);tile.append(elt('div','verification-alert '+status[0],status[1]));
        const matched=(choice.matches||[]).map(m=>m.title+(m.year?' ('+m.year+')':'')).join(', ');
        tile.append(elt('small','',((choice.matches||[]).length)+' overlapping '+(((choice.matches||[]).length)===1?'title':'titles')));
        tile.append(elt('div','credit-note',matched));
        const inspect=elt('button','primary-button','Enlarge & compare');inspect.addEventListener('click',()=>openPortraitReview(person,choice,i));tile.append(inspect);
        if(person.quick_eligible){
          const quick=elt('button','secondary-button','Accept this single result');
          quick.addEventListener('click',()=>quickApproveSingle(person,quick));
          tile.append(quick);
        }
        grid.append(tile);
      });
      wrap.append(grid);
      const skip=elt('button','secondary-button','Skip this performer');skip.style.marginTop='12px';
      skip.addEventListener('click',async()=>{
        skip.disabled=true;
        try{await post('/api/enrich/skip',{key:person.key});await refreshEnrichment(true);}
        catch(e){notify('Could not skip: '+e.message);skip.disabled=false;}
      });
      wrap.append(skip);host.append(wrap);
    }
  }
  async function acceptQueuedSingles(){
    const button=$('enrichAcceptUnique');button.disabled=true;
    try{
      const r=await post('/api/enrich/accept-unique',{});
      notify(r.started?'Processing single-result review entries in the background.':'Single-result approvals are already running.');
      await refreshEnrichment(true);
    }catch(e){notify('Could not process singles: '+e.message);button.disabled=false;}
  }
  async function startEnrichment(){
    try{const result=await post('/api/enrich/start',{});notify(result.started?'Background portrait scan started.':'Artwork scan is already running.');await refreshEnrichment(true);}
    catch(e){notify('Could not start enrichment: '+e.message);}
  }
  async function pauseEnrichment(){
    try{await post('/api/enrich/stop',{});notify('Scan will pause after its current performer.');await refreshEnrichment();}
    catch(e){notify(e.message);}
  }
  async function saveArtSettings(e){e.preventDefault();try{
    await post('/api/art/config',{tmdb:$('tmdbToken').value.trim(),theporndb:$('tpdbToken').value.trim()});
    $('tmdbToken').value='';$('tpdbToken').value='';$('artSettingsStatus').textContent='Artwork provider credentials saved.';notify('Portrait providers saved.');
  }catch(err){$('artSettingsStatus').textContent=err.message}}
  async function findArt(key){
    const picker=$('artPicker');if(!picker)return;
    picker.replaceChildren(elt('p','note','Searching your enabled portrait providers…'));
    try{const data=await api('/api/art/search?key='+encodeURIComponent(key));picker.replaceChildren();
      const h=elt('h3','','Choose a portrait for '+data.actor);picker.append(h);
      picker.append(elt('p','note','Matches are suggestions only. Confirm the image represents the right person before applying.'));
      const providers=elt('p','note','TMDB: '+(data.configured.tmdb?'enabled':'not enabled')+' · ThePornDB fallback: '+(data.configured.theporndb?'ready':'add a token')+' · Wikimedia: disabled');picker.append(providers);
      for(const warning of data.warnings){picker.append(elt('p','note',warning));}
      if(!data.results.length){picker.append(elt('p','note','No portraits found. Add provider keys in Settings or try again later.'));return;}
      const results=elt('div','art-choice-grid');
      for(const art of data.results){
        const card=elt('div','art-choice');card.append(imageOrInitials(art.preview,art.name,'art-choice-photo'));
        card.append(elt('strong','',art.name),elt('small','',art.source));
        const sourceLink=document.createElement('a');sourceLink.href=art.reference;sourceLink.target='_blank';sourceLink.rel='noopener noreferrer';sourceLink.textContent='Verify source';card.append(sourceLink);
        const use=elt('button','secondary-button','Use portrait');use.type='button';use.addEventListener('click',async()=>{
          use.disabled=true;use.textContent='Saving…';try{await post('/api/art/apply',{key,id:art.id});state.artRevision=Date.now();await openActor(key);await loadActors(false);notify('Portrait saved locally.');}
          catch(error){notify('Could not save portrait: '+error.message);use.disabled=false;use.textContent='Use portrait';}
        });card.append(use);results.append(card);
      }
      picker.append(results);
    }catch(e){picker.replaceChildren(elt('p','note','Artwork search failed: '+e.message))}
  }
  async function removeArt(key){try{await post('/api/art/remove',{key});state.artRevision=Date.now();await openActor(key);await loadActors(false);notify('Custom portrait removed; using Plex image again.')}catch(e){notify(e.message)}}
  async function openActor(key){modal('actorOverlay',true);$('actorDetail').replaceChildren(elt('p','','Loading performer…'));
    try{const actor=await api('/api/actor?key='+encodeURIComponent(key));const host=$('actorDetail');host.replaceChildren();
      const header=elt('div','actor-header');header.append(imageOrInitials(actor.image ? actor.image+'&v='+state.artRevision : '',actor.name,'actor-avatar'));
      const right=elt('div');right.append(elt('div','eyebrow','PERFORMER PROFILE'));const h=elt('h2','',actor.name);h.id='actorName';right.append(h,elt('p','actor-caption',formatNumber(actor.titles.length)+' '+(actor.titles.length===1?'title':'titles')+' in your Plex collection'));
      if(actor.art?.source){const artNote=elt('p','note','Portrait: '+actor.art.source);if(actor.art.source_url){const a=document.createElement('a');a.href=actor.art.source_url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=' · Source / license';artNote.append(a);}right.append(artNote);}
      if(state.admin){const artActions=elt('div','art-actions');const search=elt('button','secondary-button','Find portrait');search.type='button';search.addEventListener('click',()=>findArt(key));artActions.append(search);
        if(actor.art?.source && actor.art.source!=='Plex'){const remove=elt('button','secondary-button','Remove custom portrait');remove.type='button';remove.addEventListener('click',()=>removeArt(key));artActions.append(remove);}right.append(artActions);}
      header.append(right);host.append(header);
      if(state.admin){const picker=elt('div','art-picker');picker.id='artPicker';host.append(picker);}host.append(elt('div','section-divider'));
      host.append(elt('h3','filmography-heading','In your library'));
      const grid=elt('div','film-grid');for(const title of actor.titles){const tile=elt('div','film-item');const a=document.createElement('a');a.href=plexLink(title.key);a.target='_blank';a.rel='noopener noreferrer';a.title='Open '+title.title+' in Plex';
        const poster=elt('div','film-poster');if(title.image){const im=document.createElement('img');im.src=title.image;im.loading='lazy';im.alt='';im.addEventListener('error',()=>{im.remove();poster.textContent='▤'});poster.append(im)}else{poster.textContent='▤'}
        a.append(poster,elt('strong','',title.title));tile.append(a);tile.append(elt('small','',[(title.year||'Year unknown'),title.library].join(' · ')));if(title.character)tile.append(elt('small','',title.character));grid.append(tile)}host.append(grid);
    }catch(e){$('actorDetail').textContent='Could not load this performer: '+e.message}
  }
  async function refreshStatus(){try{const s=await api('/api/status');const progress=$('syncBanner');progress.hidden=!s.running&&s.phase==='Not scanned';const hasImageSummary=!!(s.portrait_missing||s.portrait_failed||s.portrait_skipped);if(s.running||s.phase==='Sync failed'||s.phase==='Finished with warnings'||hasImageSummary){
      progress.hidden=false;
      $('syncPhase').textContent=s.phase;
      const unit=s.phase==='Caching Plex actor portraits'||((s.phase==='Finished'||s.phase==='Finished with warnings')&&(s.portrait_downloaded||s.portrait_missing||s.portrait_failed||s.portrait_skipped))?'portraits':s.phase==='Resolving Plex actor artwork'?'performers':'titles';
      $('syncFraction').textContent=s.total?formatNumber(s.current)+' / '+formatNumber(s.total)+' '+unit:'';
      $('syncBar').style.width=s.total?Math.min(100,Math.round(s.current/s.total*100))+'%':'3%';
      const details=[];
      if(s.phase==='Caching Plex actor portraits'||s.portrait_downloaded||s.portrait_missing||s.portrait_failed){
        details.push(formatNumber(s.portrait_downloaded||0)+' downloaded');
        if(s.portrait_missing)details.push(formatNumber(s.portrait_missing)+' missing in Plex');
        if(s.portrait_skipped)details.push(formatNumber(s.portrait_skipped)+' skipped due to source errors');
      }
      if(s.errors)details.push(formatNumber(s.errors)+' error(s)');
      if(s.last_error)details.push('Latest: '+s.last_error);
      $('syncError').textContent=details.join(' · ');
    }else if(!s.running)progress.hidden=true;
    $('refreshBtn').disabled=!!s.running;
    if(s.running){state.wasRunning=true;}else if(state.wasRunning){state.wasRunning=false;notify(s.errors?'Index completed with warnings.':'Your cast directory is up to date.');await loadStats();await loadActors(false)}
  }catch(e){console.warn(e)}}
  async function sync(force=false){try{const result=await post('/api/sync',{force});if(result.started){notify('Indexing started. You can keep browsing while it runs.');state.wasRunning=true;await refreshStatus()}else notify('Indexing is already in progress.')}catch(e){notify('Could not sync: '+e.message)}}
  async function saveSettings(event){event.preventDefault();$('settingsError').textContent='';const url=$('plexUrl').value.trim();const token=$('plexToken').value.trim();try{await post('/api/config',{url,token:token||null});state.tokenSet=true;modal('settingsOverlay',false);$('connDot').classList.add('online');$('connectionLabel').textContent='Plex configured';await sync();}catch(e){$('settingsError').textContent=e.message}}
  async function start(){
    $('artSettingsForm').addEventListener('submit',saveArtSettings);$('enrichStart').addEventListener('click',startEnrichment);$('enrichAcceptUnique').addEventListener('click',acceptQueuedSingles);$('enrichPause').addEventListener('click',pauseEnrichment);$('enrichReload').addEventListener('click',()=>refreshEnrichment(true));$('enrichRetry').addEventListener('click',async()=>{try{const r=await post('/api/enrich/retry-errors',{});notify('Reset '+r.reset+' failed lookups. Click Start / resume to retry them.');await refreshEnrichment(true);}catch(e){notify(e.message)}});$('enrichRetryUnmatched').addEventListener('click',async()=>{try{const r=await post('/api/enrich/retry-unmatched',{});notify('Requeued '+r.reset+' unmatched performers. Click Start / resume to search with the updated provider order.');await refreshEnrichment(true);}catch(e){notify(e.message)}});$('settingsBtn').addEventListener('click',openSettings);$('settingsTopBtn').addEventListener('click',openSettings);$('reviewClose').addEventListener('click',()=>modal('reviewOverlay',false));document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('reviewOverlay').hidden)modal('reviewOverlay',false)});$('settingsClose').addEventListener('click',()=>modal('settingsOverlay',false));$('settingsCancel').addEventListener('click',()=>modal('settingsOverlay',false));$('settingsForm').addEventListener('submit',saveSettings);
    $('actorClose').addEventListener('click',()=>modal('actorOverlay',false));$('settingsOverlay').addEventListener('click',e=>{if(e.target===$('settingsOverlay'))modal('settingsOverlay',false)});$('actorOverlay').addEventListener('click',e=>{if(e.target===$('actorOverlay'))modal('actorOverlay',false)});document.addEventListener('keydown',e=>{if(e.key==='Escape'){modal('settingsOverlay',false);modal('actorOverlay',false)}});
    $('adminLogoutBtn').addEventListener('click',async()=>{try{await post('/api/admin/logout',{});location.assign('/');}catch(e){notify(e.message)}});$('emptyAction').addEventListener('click',openSettings);$('logoutBtn').addEventListener('click',async()=>{try{await post('/api/logout',{});location.assign('/login')}catch(e){notify(e.message)}});$('refreshBtn').addEventListener('click',()=>sync());$('loadMore').addEventListener('click',()=>loadActors(true));$('sortSelect').addEventListener('change',e=>{state.sort=e.target.value;loadActors(false)});$('missingOnly').addEventListener('change',e=>{state.missing=e.target.checked;loadActors(false)});let typing;
    $('searchInput').addEventListener('input',e=>{clearTimeout(typing);typing=setTimeout(()=>{state.search=e.target.value;loadActors(false)},180)});
    $('mediaNav').addEventListener('click',e=>{const button=e.target.closest('[data-type]');if(!button)return;state.type=button.dataset.type;renderMediaNav();loadActors(false)});
    buildAlphabet();try{const c=await api('/api/config');state.tokenSet=c.token_set;state.admin=!!c.admin;
      $('adminLoginLink').hidden=state.admin||!c.admin_login_available; $('adminLogoutBtn').hidden=!state.admin||!c.admin_login_available; $('logoutBtn').hidden=state.admin;$('settingsBtn').hidden=!state.admin;$('settingsTopBtn').hidden=!state.admin;$('refreshBtn').hidden=!state.admin;$('emptyAction').hidden=!state.admin;$('connDot').classList.toggle('online',!!c.token_set);$('connectionLabel').textContent=c.token_set?'Plex configured':'Not configured';}catch(e){notify(e.message)}
    await Promise.all([loadStats(),getPlexLinkMode()]);await loadActors(false);await refreshStatus();state.timer=setInterval(refreshStatus,2200);setInterval(()=>refreshEnrichment(false),6000);
  }
  start();
})();
