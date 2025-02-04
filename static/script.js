

let voice_list = {
"en":[
"af_alloy",
"af_aoede",
"af_bella",
"af_jessica",
"af_kore",
"af_nicole",
"af_nova",
"af_river",
"af_sarah",
"af_sky",
"am_adam",
"am_echo",
"am_eric",
"am_fenrir",
"am_liam",
"am_michael",
"am_onyx",
"am_puck",
"am_santa",
"bf_alice",
"bf_emma",
"bf_isabella",
"bf_lily",
"bm_daniel",
"bm_fable",
"bm_george",
"bm_lewis"
],
"zh":["zf_xiaobei","zf_xiaoni","zf_xiaoxiao","zf_xiaoyi","zm_yunjian","zm_yunxi","zm_yunxia","zm_yunyang"],
"ja":["jf_alpha","jf_gongitsune","jf_nezumi","jf_tebukuro","jm_kumo"],
"fr":["ff_siwis"],
"it":["if_sara","im_nicola"],
"hi":["hf_alpha","hf_beta","hm_omega","hm_psi"],
"es":["ef_dora","em_alex","em_santa"],
"pt":["pf_dora","pm_alex","pm_santa"]
};

const welcome = {
  "zh": "你好啊我的朋友",
  "en": "Hello my friend",
  "ja": "こんにちは、私の友達",
  "fr": "Bonjour mon ami",
  "es": "Hola mi amigo",
  "pt": "Olá meu amigo",
  "it": "Ciao amico mio",
  "hi": "नमस्ते मेरे दोस्त"
};


$(document).ready(function () {
  [].forEach.call(document.querySelectorAll('[role="tooltip"]'), it => {
    new bootstrap.Tooltip(it);
  });



  const synthesisArea = $('#synthesis-area');
  const voiceSelect = $('#voice-select');
  const speedInput = $('#speed-input');
  const keepSpacingCheckbox = $('#keep-spacing-checkbox');
  const synthesisText = $('#synthesis-text');

  const startSynthesisButton = $('#start-synthesis-button');
  const startListenButton = $('#start-listen-button');

  const synthesisAudioContainer = $('#synthesis-audio-container');

  const voiceLang = $('#lang-select');

  const voiceImportSrtButton = $('#voice-import-srt-button');
  const voiceImportTextButton = $('#voice-import-text-button');






  voiceLang.on('change', function () {
    let html = [];
    voice_list[$(this).val()].forEach(n => {
      html.push(`<option value="${n}">${n}</option>`);
    });
    voiceSelect.html(html);
  });
  let html = [];
  voice_list["zh"].forEach(n => {
      html.push(`<option value="${n}">${n}</option>`);
    });
  voiceSelect.html(html);






  voiceImportSrtButton.on('change', function () {
    const file = $(this)[0].files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = function (e) {
        synthesisText.val(e.target.result)
      };
      reader.readAsText(file);
    }
  });
  voiceImportTextButton.on('click', function () {
    voiceImportSrtButton.click();
  });












  function getCurrentDateTimeString() {
    const now = new Date();

    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0'); // 月份从 0 开始，所以 + 1
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day}-${hours}-${minutes}-${seconds}`;
  }

// 开始语音合成
  startSynthesisButton.on('click', function () {
    const voice = voiceSelect.val();
    const speed = speedInput.val();

    const keepSpacing = keepSpacingCheckbox.is(':checked');
    const text = synthesisText.val();

    const auto_speed = $('#auto_speed').prop('checked');


    if (!text) {
      alert('请先输入需要合成配音的文字或导入字幕')
      return;
    }
	

    startSynthesisButton.prop('disabled', true).text('合成中...');
    synthesisAudioContainer.empty() // 清空之前的内容



    $.ajax({
      url: '/synthesize',
      type: 'POST',
	  timeout:86400000,

      contentType: 'application/json',

      data: JSON.stringify({
        voice: voice,
        speed: speed,
        keep_spacing: keepSpacing,
        text: text,
        auto_speed: auto_speed
      }),

      success: function (response, status, xhr) {
        if (response.status=='ok' && response.data) {
			const audioUrl = response.data;
            const audio = $('<audio controls></audio>').attr('src', audioUrl);

            const downloadButton = $('<button class="btn btn-sm btn-secondary">下载音频</button>').on('click', function () {
              const downloadLink = $('<a>').attr({
                href: audioUrl,
                download: 'synthesized_audio-' + getCurrentDateTimeString() + '.mp3'
              });
              $('body').append(downloadLink);
              downloadLink[0].click();
              downloadLink.remove();
            });

            synthesisAudioContainer.append(audio)
            synthesisAudioContainer.append(downloadButton)
            startSynthesisButton.prop('disabled', false).text('开始合成配音');
            return;
        }
      },
      error: function (err) {
        alert(err.responseJSON ? err.responseJSON['error'] : "Failed");
        startSynthesisButton.prop('disabled', false).text('开始合成配音');
      }

    });
  });

  startListenButton.on('click', function () {
    const voice = voiceSelect.val();

    if (!voice) {
      return alert('必须选择角色');
    }

    const text = welcome[$('#lang-select').val()];
    if (!text) {
      return alert('抱歉该角色暂不可试听')
    }
    $.ajax({
      url: '/synthesize',
      type: 'POST',
	  timeout:86400000,

      contentType: 'application/json',
      

      data: JSON.stringify({
        voice: voice,
        text: text
      }),

      success: function (response, status, xhr) {
        if(response.status=='ok' && response.data){
          const audioUrl = response.data;
          const audio = $('<audio hidden controls></audio>')
          audio.attr('src', audioUrl);
          $("body").append(audio)
          audio[0].play();
        }
      },
      error: function (err) {        
        alert(err.responseJSON ? err.responseJSON['error'] : 'Failed');
      }

    });


  });




});


