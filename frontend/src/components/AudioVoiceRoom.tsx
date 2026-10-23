import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  X,
  ShieldAlert,
  CheckCircle2,
  Bot,
  User,
  Sliders,
  Send,
  Sparkles,
  AlertCircle,
  HelpCircle,
  Play
} from 'lucide-react';
import { taskApi } from '../api/client';

interface AudioVoiceRoomProps {
  isOpen: boolean;
  onClose: () => void;
  taskTitle?: string;
  taskId?: string;
}

interface TranscriptEntry {
  speaker: 'AI Reviewer' | 'Intern' | 'System';
  text: string;
  timestamp: string;
}

export const AudioVoiceRoom: React.FC<AudioVoiceRoomProps> = ({
  isOpen,
  onClose,
  taskTitle = 'Task Briefing Session',
  taskId
}) => {
  // Session states
  const [hasConsent, setHasConsent] = useState<boolean>(false);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [aiSpeaking, setAiSpeaking] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [userInput, setUserInput] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [interimSpokenText, setInterimSpokenText] = useState<string>('');
  const [micActivityLevel, setMicActivityLevel] = useState<number>(0);

  // Voice Tuning states
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoiceIndex, setSelectedVoiceIndex] = useState<number>(0);
  const [speechRate, setSpeechRate] = useState<number>(0.95);
  const [speechPitch, setSpeechPitch] = useState<number>(1.02);
  const [showVoiceSettings, setShowVoiceSettings] = useState<boolean>(false);
  const [hasMicPermissionError, setHasMicPermissionError] = useState<boolean>(false);
  const [activeVoiceName, setActiveVoiceName] = useState<string>('Subha (Cartesia Neural Voice)');

  // References
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recognitionRef = useRef<any>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const isAiSpeakingRef = useRef<boolean>(false);
  const isMutedRef = useRef<boolean>(false);

  // Keep ref synchronized with state
  useEffect(() => {
    isAiSpeakingRef.current = aiSpeaking;
  }, [aiSpeaking]);

  useEffect(() => {
    isMutedRef.current = isMuted;
    if (recognitionRef.current) {
      if (isMuted) {
        try { recognitionRef.current.stop(); } catch (e) { /* ignore */ }
      } else if (hasConsent && !aiSpeaking) {
        try { recognitionRef.current.start(); } catch (e) { /* ignore */ }
      }
    }
  }, [isMuted, hasConsent, aiSpeaking]);

  // Auto-scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, interimSpokenText]);

  // Load and populate speech synthesis voices (prioritizing natural Indian English)
  useEffect(() => {
    const updateVoices = () => {
      if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
      const allVoices = window.speechSynthesis.getVoices();
      if (!allVoices || allVoices.length === 0) return;

      // Filter to English voices
      const englishVoices = allVoices.filter(v => v.lang.startsWith('en'));
      setAvailableVoices(englishVoices.length > 0 ? englishVoices : allVoices);

      // Prioritize Indian-English voices (e.g. Google English (India), Microsoft Ravi, Heera, etc.)
      const indianVoiceIdx = englishVoices.findIndex(v =>
        v.lang === 'en-IN' ||
        v.lang === 'en_IN' ||
        v.name.toLowerCase().includes('india') ||
        v.name.toLowerCase().includes('ravi') ||
        v.name.toLowerCase().includes('heera')
      );

      if (indianVoiceIdx !== -1) {
        setSelectedVoiceIndex(indianVoiceIdx);
      } else {
        // Fallback to high-quality natural voice if available
        const naturalVoiceIdx = englishVoices.findIndex(v =>
          v.name.toLowerCase().includes('natural') ||
          v.name.toLowerCase().includes('google')
        );
        setSelectedVoiceIndex(naturalVoiceIdx !== -1 ? naturalVoiceIdx : 0);
      }
    };

    updateVoices();
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  // Initialize transcript when room opens
  useEffect(() => {
    if (isOpen) {
      setTranscript([
        {
          speaker: 'System',
          text: 'Interactive Voice Briefing Session initialized (100% Local FOSS Architecture).',
          timestamp: new Date().toLocaleTimeString()
        },
        {
          speaker: 'AI Reviewer',
          text: 'Hello, I am your AI Task Reviewer. I will be conducting this briefing. Please note: this session is recorded and transcribed locally for evaluation and audit records. Do you consent to proceed?',
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
      setHasConsent(false);
      setIsRecording(false);
      setIsMuted(false);
      setInterimSpokenText('');
      setHasMicPermissionError(false);
    } else {
      stopAllAudio();
    }
  }, [isOpen]);

  // Helper: Play natural neural voice audio from base64 (Cartesia AI)
  const playAudioBase64 = (base64Data: string, onEndCallback?: () => void): boolean => {
    try {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }

      const audio = new Audio(`data:audio/mp3;base64,${base64Data}`);
      currentAudioRef.current = audio;

      setAiSpeaking(true);
      // Temporarily pause STT while AI speaks to prevent audio loopback
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) { /* ignore */ }
      }

      audio.onended = () => {
        setAiSpeaking(false);
        currentAudioRef.current = null;
        if (onEndCallback) onEndCallback();
        // Resume STT after AI finishes speaking
        if (!isMutedRef.current && recognitionRef.current) {
          setTimeout(() => {
            try { recognitionRef.current.start(); } catch (e) { /* ignore */ }
          }, 300);
        }
      };

      audio.onerror = (e) => {
        console.warn('Audio playback error:', e);
        setAiSpeaking(false);
        currentAudioRef.current = null;
        if (onEndCallback) onEndCallback();
      };

      audio.play().catch((err) => {
        console.warn('HTML5 audio play rejected:', err);
        setAiSpeaking(false);
        currentAudioRef.current = null;
        if (onEndCallback) onEndCallback();
      });

      return true;
    } catch (err) {
      console.warn('Error in playAudioBase64:', err);
      return false;
    }
  };

  // Instant interrupt: stops AI talking and lets user speak immediately
  const handleInterruptAI = () => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setAiSpeaking(false);
    if (!isMutedRef.current && recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (e) {
        /* ignore */
      }
    }
  };

  // Helper: Speak text using Web Speech API as resilient fallback
  const speakText = (text: string, onEndCallback?: () => void) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      if (onEndCallback) onEndCallback();
      return;
    }

    try {
      window.speechSynthesis.cancel(); // Stop any pending speech

      // Clean markdown, symbols, and formatting for spoken cadence
      const cleanSpoken = text
        .replace(/[\*#_`~>\[\]]/g, '')
        .replace(/\bhttps?:\/\/\S+/gi, 'the specified web link')
        .replace(/\s+/g, ' ')
        .trim();

      const utterance = new SpeechSynthesisUtterance(cleanSpoken);
      if (availableVoices[selectedVoiceIndex]) {
        utterance.voice = availableVoices[selectedVoiceIndex];
      }
      utterance.rate = speechRate;
      utterance.pitch = speechPitch;

      utterance.onstart = () => {
        setAiSpeaking(true);
        // Temporarily pause STT while AI speaks to prevent echo
        if (recognitionRef.current) {
          try { recognitionRef.current.stop(); } catch (e) { /* ignore */ }
        }
      };

      utterance.onend = () => {
        setAiSpeaking(false);
        if (onEndCallback) onEndCallback();
        // Resume STT after AI finishes speaking
        if (!isMutedRef.current && recognitionRef.current) {
          setTimeout(() => {
            try { recognitionRef.current.start(); } catch (e) { /* ignore */ }
          }, 300);
        }
      };

      utterance.onerror = (e) => {
        console.warn('Speech synthesis error:', e);
        setAiSpeaking(false);
        if (onEndCallback) onEndCallback();
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('Error invoking speech synthesis:', err);
      setAiSpeaking(false);
      if (onEndCallback) onEndCallback();
    }
  };

  // Test humanized neural voice (Subha) with fallback to browser TTS
  const handleTestVoice = async () => {
    const sample = 'Hello! I am Subha, your AI Task Reviewer. I will guide you through your project objectives, requirements, and evaluation criteria.';
    try {
      setIsProcessing(true);
      const res = await taskApi.synthesizeSpeech(sample);
      if (res && res.audio_base64) {
        playAudioBase64(res.audio_base64);
        if (res.voice_name) setActiveVoiceName(res.voice_name);
      } else {
        speakText(sample);
      }
    } catch (err) {
      speakText(sample);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle granting consent and start live briefing
  const handleGrantConsent = async () => {
    setHasConsent(true);
    setTranscript((prev) => [
      ...prev,
      {
        speaker: 'Intern',
        text: 'I acknowledge the AI disclosure and consent to audio recording and transcription.',
        timestamp: new Date().toLocaleTimeString()
      }
    ]);

    // Initialize microphone and STT recognition
    await startMicrophoneAndSTT();

    // Trigger initial AI Task Briefing from backend
    try {
      setIsProcessing(true);
      let briefingReply = '';
      let audioBase64: string | null = null;

      if (taskId) {
        const res = await taskApi.voiceChat(taskId, 'start_briefing', 'BRIEFING');
        briefingReply = res.reply;
        audioBase64 = res.audio_base64 || null;
        if (res.voice_name) setActiveVoiceName(res.voice_name);
      } else {
        briefingReply =
          'Hello! I am Subha, your AI Task Reviewer. What questions can I answer for you regarding the task requirements?';
      }

      setTranscript((prev) => [
        ...prev,
        {
          speaker: 'AI Reviewer',
          text: briefingReply,
          timestamp: new Date().toLocaleTimeString()
        }
      ]);

      if (audioBase64) {
        playAudioBase64(audioBase64);
      } else {
        speakText(briefingReply);
      }
    } catch (err) {
      const fallbackReply =
        'Hello! I am Subha, your AI Task Reviewer. What questions can I answer for you regarding the task requirements?';
      setTranscript((prev) => [
        ...prev,
        {
          speaker: 'AI Reviewer',
          text: fallbackReply,
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
      speakText(fallbackReply);
    } finally {
      setIsProcessing(false);
    }
  };

  // Setup Microphone & Continuous Speech Recognition (STT)
  const startMicrophoneAndSTT = async () => {
    // 1. AudioContext & Visualizer
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      mediaStreamRef.current = stream;
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      setIsRecording(true);
      setHasMicPermissionError(false);
      drawWaveform();
    } catch (err) {
      console.warn('Microphone stream access unavailable or denied:', err);
      setHasMicPermissionError(true);
    }

    // 2. Browser Speech Recognition (STT)
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-IN'; // Default to Indian English recognition

        recognition.onstart = () => {
          setIsRecording(true);
        };

        recognition.onresult = (event: any) => {
          // Ignore input if AI is speaking or mic is muted
          if (isAiSpeakingRef.current || isMutedRef.current) return;

          let interim = '';
          let finalTranscript = '';

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const piece = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += piece;
            } else {
              interim += piece;
            }
          }

          if (interim) {
            setInterimSpokenText(interim);
          }

          if (finalTranscript.trim()) {
            setInterimSpokenText('');
            handleProcessUserMessage(finalTranscript.trim());
          }
        };

        recognition.onerror = (event: any) => {
          if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            setHasMicPermissionError(true);
          }
        };

        recognition.onend = () => {
          // Automatically restart recognition if session is active and not muted
          if (!isAiSpeakingRef.current && !isMutedRef.current && hasConsent) {
            try {
              recognition.start();
            } catch (e) {
              /* ignore */
            }
          }
        };

        recognitionRef.current = recognition;
        recognition.start();
      } catch (err) {
        console.warn('SpeechRecognition initialization error:', err);
      }
    } else {
      console.info('SpeechRecognition API not supported in this browser. Fallback to typed voice interaction.');
    }
  };

  // Waveform renderer & mic volume calculation
  const drawWaveform = () => {
    if (!canvasRef.current || !analyserRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const render = () => {
      analyserRef.current?.getByteFrequencyData(dataArray);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Calculate average volume activity level
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      const avg = sum / bufferLength;
      setMicActivityLevel(Math.min(100, Math.round((avg / 128) * 100)));

      // Voice Barge-in: If AI is speaking and user speaks firmly (avg > 30), automatically interrupt AI!
      if (isAiSpeakingRef.current && avg > 30) {
        handleInterruptAI();
      }

      const barWidth = (canvas.width / bufferLength) * 2;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height;
        ctx.fillStyle = isAiSpeakingRef.current ? '#06b6d4' : avg > 10 ? '#10b981' : '#64748b';
        ctx.fillRect(x, canvas.height - barHeight, barWidth - 2, barHeight);
        x += barWidth;
      }

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();
  };

  // Stop all audio, mic streams, and recognition
  const stopAllAudio = () => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        /* ignore */
      }
    }
    setIsRecording(false);
    setAiSpeaking(false);
  };

  // Process user spoken or typed message
  const handleProcessUserMessage = async (messageText: string) => {
    if (!messageText.trim() || isProcessing) return;

    const cleanQuestion = messageText.trim();
    setUserInput('');
    setInterimSpokenText('');

    // Add user message to transcript
    setTranscript((prev) => [
      ...prev,
      { speaker: 'Intern', text: cleanQuestion, timestamp: new Date().toLocaleTimeString() }
    ]);

    setIsProcessing(true);

    try {
      let replyText = '';
      let audioBase64: string | null = null;

      if (taskId) {
        const res = await taskApi.voiceChat(taskId, cleanQuestion, 'BRIEFING');
        replyText = res.reply;
        audioBase64 = res.audio_base64 || null;
        if (res.voice_name) setActiveVoiceName(res.voice_name);
      } else {
        // Fallback intelligent responder
        const lower = cleanQuestion.toLowerCase();
        if (lower.includes('deadline') || lower.includes('time') || lower.includes('date')) {
          replyText =
            'The deadline is strictly 7 days from task assignment in Asia/Kolkata timezone. Please submit before the cutoff.';
        } else if (lower.includes('rubric') || lower.includes('pass') || lower.includes('score')) {
          replyText =
            'Our evaluation rubric weights unit test pass rate at 60% and code quality at 40%. All mandatory criteria must pass.';
        } else if (lower.includes('appeal') || lower.includes('dispute')) {
          replyText =
            'If you dispute any evaluation outcome, you can submit an appeal through your dashboard for human assigner review.';
        } else {
          replyText =
            'I understand your inquiry. Please ensure all implementation deliverables pass deterministic tests and adhere to the project specification.';
        }
      }

      // Add AI reply to transcript and speak aloud
      setTranscript((prev) => [
        ...prev,
        { speaker: 'AI Reviewer', text: replyText, timestamp: new Date().toLocaleTimeString() }
      ]);

      if (audioBase64) {
        playAudioBase64(audioBase64);
      } else {
        speakText(replyText);
      }
    } catch (err: any) {
      const errReply =
        'I received your question. Please ensure all your test cases pass and your code is pushed to the repository before the deadline.';
      setTranscript((prev) => [
        ...prev,
        { speaker: 'AI Reviewer', text: errReply, timestamp: new Date().toLocaleTimeString() }
      ]);
      speakText(errReply);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleManualSend = () => {
    if (userInput.trim()) {
      handleProcessUserMessage(userInput.trim());
    }
  };

  const handleClose = () => {
    stopAllAudio();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-4">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col h-[680px]">
        {/* Header */}
        <div className="p-4 bg-slate-800/90 border-b border-slate-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-600 to-blue-600 flex items-center justify-center text-white shadow-md shadow-cyan-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-100 text-sm sm:text-base">AI Voice Briefing Room</h3>
                <span className="text-[10px] bg-gradient-to-r from-emerald-950 to-teal-950 text-emerald-300 border border-emerald-700/80 px-2 py-0.5 rounded-full font-semibold flex items-center gap-1 shadow-sm">
                  <Sparkles className="w-3 h-3 text-emerald-400" />
                  Subha (Cartesia Neural)
                </span>
              </div>
              <p className="text-xs text-slate-400 truncate max-w-sm">{taskTitle}</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowVoiceSettings(!showVoiceSettings)}
              className={`p-2 rounded-lg border text-xs font-medium flex items-center gap-1 transition-colors ${
                showVoiceSettings
                  ? 'bg-cyan-950/80 border-cyan-600 text-cyan-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
              title="Voice & Speech Settings"
            >
              <Sliders className="w-4 h-4" />
              <span className="hidden sm:inline">Voice Tuning</span>
            </button>
            <button
              onClick={handleClose}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Voice Tuning Settings Drawer */}
        {showVoiceSettings && (
          <div className="p-4 bg-slate-950 border-b border-slate-800 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-200 flex items-center gap-1.5">
                <Volume2 className="w-4 h-4 text-cyan-400" />
                Humanized Voice Settings
              </span>
              <button
                onClick={handleTestVoice}
                className="flex items-center gap-1 px-2.5 py-1 bg-cyan-600/30 hover:bg-cyan-600/40 border border-cyan-500/50 rounded-lg text-cyan-300 font-semibold transition-colors"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>Test Voice Sample</span>
              </button>
            </div>

            <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60 flex items-center justify-between text-[11px] text-emerald-200">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>
                  <strong>Active Neural Voice:</strong> {activeVoiceName}
                </span>
              </div>
              <span className="px-2 py-0.5 bg-emerald-900/60 border border-emerald-600/50 rounded text-emerald-300 font-mono text-[10px]">
                Cartesia Sonic
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Fallback Browser Voice</label>
                <select
                  value={selectedVoiceIndex}
                  onChange={(e) => setSelectedVoiceIndex(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 font-medium focus:outline-none focus:border-cyan-500"
                >
                  {availableVoices.map((voice, idx) => (
                    <option key={idx} value={idx}>
                      {voice.lang.includes('IN') ? '🇮🇳 ' : '🌐 '}
                      {voice.name} ({voice.lang})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">
                  Speed: <span className="text-cyan-400 font-mono">{speechRate}x</span>
                </label>
                <input
                  type="range"
                  min="0.8"
                  max="1.2"
                  step="0.05"
                  value={speechRate}
                  onChange={(e) => setSpeechRate(Number(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">
                  Pitch: <span className="text-cyan-400 font-mono">{speechPitch}x</span>
                </label>
                <input
                  type="range"
                  min="0.85"
                  max="1.15"
                  step="0.05"
                  value={speechPitch}
                  onChange={(e) => setSpeechPitch(Number(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
              </div>
            </div>
          </div>
        )}

        {/* Mandatory Transparency & Consent Notice */}
        {!hasConsent ? (
          <div className="p-8 flex-1 flex flex-col items-center justify-center text-center space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-lg shadow-amber-500/10">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <div className="max-w-md space-y-2">
              <h4 className="text-lg font-bold text-slate-100">Mandatory AI Disclosure & Recording Consent</h4>
              <p className="text-sm text-slate-400 leading-relaxed">
                You are entering a live session with an <strong className="text-cyan-400">AI Task Reviewer</strong>.
                This agent is an autonomous software system. All speech is transcribed and evaluated against rubric
                acceptance criteria on local workspace infrastructure.
              </p>
            </div>

            <div className="p-4 bg-slate-800/60 border border-slate-700/50 rounded-xl text-xs text-slate-300 text-left max-w-md space-y-2">
              <div className="flex items-center gap-1.5 font-semibold text-slate-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Zero Cloud AI Exposure</span>
              </div>
              <p className="text-slate-400 leading-relaxed">
                Speech recognition, Ollama language inference, and audio synthesis run 100% on self-hosted local
                infrastructure with complete privacy.
              </p>
            </div>

            <div className="flex space-x-3 pt-2">
              <button
                onClick={handleClose}
                className="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              >
                Decline & Exit
              </button>
              <button
                onClick={handleGrantConsent}
                className="px-6 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-600/30 transition-all active:scale-95"
              >
                I Consent & Join Voice Briefing
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Live Audio Visualizer Bar */}
            <div className="bg-slate-950/80 p-3.5 border-b border-slate-800 flex items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className="relative">
                  <span
                    className={`w-3.5 h-3.5 rounded-full block ${
                      aiSpeaking
                        ? 'bg-cyan-400 animate-ping'
                        : isMuted
                        ? 'bg-rose-500'
                        : micActivityLevel > 15
                        ? 'bg-emerald-400 animate-pulse'
                        : 'bg-slate-500'
                    }`}
                  />
                  <span
                    className={`w-3.5 h-3.5 rounded-full absolute top-0 left-0 ${
                      aiSpeaking
                        ? 'bg-cyan-400'
                        : isMuted
                        ? 'bg-rose-500'
                        : micActivityLevel > 15
                        ? 'bg-emerald-400'
                        : 'bg-slate-500'
                    }`}
                  />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-200">
                    {aiSpeaking
                      ? `AI Speaking (${activeVoiceName})`
                      : isMuted
                      ? 'Microphone Muted'
                      : micActivityLevel > 15
                      ? 'Hearing Your Voice...'
                      : 'Listening for Your Question...'}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    {aiSpeaking ? `Output: ${activeVoiceName}` : isMuted ? 'Mic off' : `Mic Activity: ${micActivityLevel}%`}
                  </div>
                </div>
              </div>

              {/* Dynamic Waveform Canvas */}
              <canvas
                ref={canvasRef}
                width={200}
                height={28}
                className="hidden sm:block rounded bg-slate-900 border border-slate-800"
              />

              {/* Mic & Interrupt Controls */}
              <div className="flex items-center space-x-2">
                {aiSpeaking && (
                  <button
                    onClick={handleInterruptAI}
                    className="px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-colors bg-amber-950/80 border-amber-600/80 text-amber-300 hover:bg-amber-900 shadow-md animate-pulse"
                    title="Stop AI speech immediately and let me speak"
                  >
                    <span>⏹ Stop & Speak</span>
                  </button>
                )}
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                    isMuted
                      ? 'bg-rose-950/70 border-rose-700/60 text-rose-300'
                      : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
                  }`}
                >
                  {isMuted ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5 text-emerald-400" />}
                  <span>{isMuted ? 'Unmute' : 'Mute Mic'}</span>
                </button>
              </div>
            </div>

            {/* Permission Warning if Microphone Blocked */}
            {hasMicPermissionError && (
              <div className="bg-amber-950/60 border-b border-amber-800/80 px-4 py-2 text-xs text-amber-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <span>
                  Microphone access is not permitted in this browser tab. You can still ask questions by typing below!
                </span>
              </div>
            )}

            {/* Live Transcript Stream */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-900/60">
              {transcript.map((item, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${
                    item.speaker === 'Intern'
                      ? 'items-end'
                      : item.speaker === 'AI Reviewer'
                      ? 'items-start'
                      : 'items-center'
                  }`}
                >
                  {item.speaker === 'System' ? (
                    <div className="text-[11px] text-slate-500 font-mono py-1 px-3 bg-slate-800/50 rounded-full border border-slate-800">
                      {item.text}
                    </div>
                  ) : (
                    <div
                      className={`max-w-[85%] rounded-2xl p-3.5 text-sm shadow-md ${
                        item.speaker === 'Intern'
                          ? 'bg-blue-600 text-white rounded-br-none'
                          : 'bg-slate-800/90 border border-slate-700/80 text-slate-200 rounded-bl-none'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        <span
                          className={`text-[10px] font-bold uppercase tracking-wider ${
                            item.speaker === 'Intern' ? 'text-blue-200' : 'text-cyan-400'
                          }`}
                        >
                          {item.speaker === 'Intern' ? 'Intern (You)' : 'AI Task Reviewer'}
                        </span>
                        <span className="text-[10px] text-slate-400">{item.timestamp}</span>
                      </div>
                      <p className="leading-relaxed whitespace-pre-wrap">{item.text}</p>
                    </div>
                  )}
                </div>
              ))}

              {/* Real-time speech captioning preview */}
              {interimSpokenText && (
                <div className="flex flex-col items-end">
                  <div className="max-w-[85%] rounded-2xl p-3 text-xs bg-slate-800/80 border border-cyan-500/50 text-cyan-200 animate-pulse rounded-br-none">
                    <div className="flex items-center gap-1.5 font-bold mb-1 text-[10px] uppercase text-cyan-400">
                      <Mic className="w-3 h-3 text-cyan-400 animate-bounce" />
                      <span>Transcribing Voice...</span>
                    </div>
                    <p className="italic">"{interimSpokenText}"</p>
                  </div>
                </div>
              )}

              {/* AI Processing Indicator */}
              {isProcessing && (
                <div className="flex flex-col items-start">
                  <div className="rounded-2xl p-3 text-xs bg-slate-800/80 border border-slate-700 text-slate-400 rounded-bl-none flex items-center gap-2">
                    <div className="w-3 h-3 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                    <span>AI Reviewer is thinking...</span>
                  </div>
                </div>
              )}

              <div ref={transcriptEndRef} />
            </div>

            {/* Input Bar (Voice + Typed Clarification) */}
            <div className="p-3 bg-slate-800/80 border-t border-slate-700 flex items-center space-x-2">
              <input
                type="text"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleManualSend()}
                placeholder="Speak into your mic or type a question (e.g. 'What is the deadline?')..."
                disabled={isProcessing}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={handleManualSend}
                disabled={!userInput.trim() || isProcessing}
                className="px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-sm font-semibold rounded-xl shadow-md transition-all flex items-center gap-1.5"
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline">Send</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
