<template>
  <div class="chat-container">
    <!-- Chat header -->
    <div class="chat-header">
      <h1 class="chat-title">Curio</h1>
    </div>

    <!-- Chat messages area -->
    <div class="chat-messages" ref="messagesContainer">
      
      <div 
        v-for="(msg, index) in chatHistory" 
        :key="index" 
        :class="`message ${msg.role}`"
      >
        <div class="message-bubble">
          <div class="message-text">{{ msg.content }}</div>
          <div class="message-time">{{ msg.time }}</div>
        </div>
      </div>
    </div>

    <!-- Push-to-talk area -->
    <div class="chat-input-area">
      <div class="push-to-talk-container">
        <button 
          @mousedown="handleMouseDown"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseLeave"
          :disabled="isLoading"
          :class="`push-to-talk-button ${isRecording ? 'recording' : ''} ${isLoading ? 'loading' : ''}`"
        >
          <div class="button-content">
            <span v-if="isLoading" class="loading-icon">⏳</span>
            <span v-else-if="isRecording" class="recording-icon">🎤</span>
            <span v-else class="mic-icon">🎤</span>
            <div class="button-text">
              {{ isLoading ? 'Processing...' : isRecording ? 'Recording...' : 'Hold to Speak' }}
            </div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
// Use relative paths - works with nginx reverse proxy (local) and Ingress (prod)

// Props
const props = defineProps<{
  selectedImagePath?: string
}>()
// State
const isLoading = ref(false)
const isRecording = ref(false)
const chatHistory = ref<Array<{role: string, content: string, time: string}>>([])
const messagesContainer = ref<HTMLElement>()
const convState = ref<'greet' | 'scaffolding' | 'scienceqa_init' | 'scienceqa' | 'reflection' | 'close'>('greet')
const conversationId = ref<string>(crypto.randomUUID())
const sessionId = ref<string>(crypto.randomUUID())

// Audio recording
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
// Unused - kept for potential future use with analyzeAudioBlob
// let audioContext: AudioContext | null = null
let recorderMimeType = ''
let currentAudio: HTMLAudioElement | null = null
// Call backend transcription API
const transcribeWithBackend = async (audioBlob: Blob): Promise<string> => {
  const formData = new FormData()
  const ext = audioBlob.type.includes('webm') ? 'webm' :
               audioBlob.type.includes('ogg') ? 'ogg' :
               audioBlob.type.includes('mp3') ? 'mp3' : 'wav'
  formData.append('audio', audioBlob, `recording.${ext}`)

  const resp = await fetch('/api/transcribe', {
    method: 'POST',
    body: formData
  })

  if (!resp.ok) {
    const errText = await resp.text().catch(() => '')
    throw new Error(`Transcription failed: ${resp.status} ${errText}`)
  }

  const json = await resp.json()
  return json.text as string
}

// Analyze audio to detect invalid inputs (too short, tiny size, near-silence)
// Unused function - kept for potential future use
// const analyzeAudioBlob = async (audioBlob: Blob): Promise<{ durationSec: number; peak: number; rms: number }> => {
//   if (!audioContext) {
//     audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
//   }
//   const arrayBuf = await audioBlob.arrayBuffer()
//   const audioBuf = await audioContext.decodeAudioData(arrayBuf)
//   const channelData = audioBuf.getChannelData(0)
//   let peak = 0
//   let sumSquares = 0
//   for (let i = 0; i < channelData.length; i++) {
//     const v = channelData[i] ?? 0
//     const av = Math.abs(v)
//     if (av > peak) peak = av
//     sumSquares += v * v
//   }
//   const rms = Math.sqrt(sumSquares / channelData.length)
//   return { durationSec: audioBuf.duration ?? 0, peak, rms }
// }

// Unused function - kept for potential future use
// const isInvalidAudio = async (audioBlob: Blob): Promise<boolean> => {
//   // Size heuristic: extremely small payloads are likely invalid
//   if (audioBlob.size < 2000) return true
//   try {
//     const { durationSec, peak, rms } = await analyzeAudioBlob(audioBlob)
//     // Too short
//     if (durationSec < 0.6) return true
//     // Near-silence thresholds (tuned conservatively)
//     if (peak < 0.01 && rms < 0.005) return true
//     return false
//   } catch {
//     // If decoding fails, be conservative and allow transcription
//     return false
//   }
// }

const getCurrentTime = () => {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const handleMouseDown = async () => {
  if (!isRecording.value && !isLoading.value) {
    await startRecording()
  }
}

const handleMouseUp = () => {
  if (isRecording.value) {
    stopRecording()
  }
}

const handleMouseLeave = () => {
  if (isRecording.value) {
    stopRecording()
  }
}

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    recorderMimeType = mediaRecorder.mimeType || 'audio/webm'
    audioChunks = []

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data)
    }

    mediaRecorder.onstop = async () => {
      const blobType = recorderMimeType || mediaRecorder?.mimeType || 'audio/webm'
      const audioBlob = new Blob(audioChunks, { type: blobType })
      await processAudio(audioBlob, blobType)
    }

    mediaRecorder.start()
    isRecording.value = true
    console.log('Recording started')
  } catch (error) {
    console.error('Error accessing microphone:', error)
  }
}

const stopRecording = () => {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.stop()
    isRecording.value = false
    console.log('Recording stopped')
  }
}

const blobToBase64 = async (blob: Blob): Promise<string> => {
  const arrayBuffer = await blob.arrayBuffer()
  const bytes = new Uint8Array(arrayBuffer)
  const chunkSize = 0x8000
  let binary = ''
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize)
    binary += String.fromCharCode(...chunk)
  }
  return btoa(binary)
}

const processAudio = async (audioBlob: Blob, mimeType: string) => {
  isLoading.value = true
  
  try {
    // 1) Transcribe audio via backend
    const userMessage = await transcribeWithBackend(audioBlob)
    
    // Add user message to chat history
    chatHistory.value.push({
      role: 'user',
      content: userMessage,
      time: getCurrentTime()
    })
    
    await scrollToBottom()
    
    // Get AI response using chat completion
    const audioBase64 = await blobToBase64(audioBlob)

    const chatResponse = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: chatHistory.value.map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        state: convState.value,
        image_path: props.selectedImagePath,
        conversation_id: conversationId.value,
        session_id: sessionId.value,
        user_audio: audioBase64,
        user_audio_mime_type: mimeType
      })
    })
    
    if (!chatResponse.ok) {
      throw new Error('Chat completion failed')
    }
    
    const chatData = await chatResponse.json()
    const aiMessage = chatData.response
    const nextState = chatData.next_state as typeof convState.value
    
    // Add AI message to chat history
    chatHistory.value.push({
      role: 'assistant',
      content: aiMessage,
      time: getCurrentTime()
    })
    convState.value = nextState
    
    await scrollToBottom()
    
    // Generate and play audio response
    await generateAndPlayAudio(aiMessage)
    
  } catch (error) {
    console.error('Error processing audio:', error)
    chatHistory.value.push({
      role: 'assistant',
      content: 'Sorry, I encountered an error. Please try again.',
      time: getCurrentTime()
    })
  } finally {
    isLoading.value = false
  }
}

const generateAndPlayAudio = async (text: string) => {
  try {
    const response = await fetch('/api/speech', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text })
    })
    
    if (!response.ok) {
      throw new Error('Speech generation failed')
    }
    
    const audioBlob = await response.blob()
    const audioUrl = URL.createObjectURL(audioBlob)
    const audio = new Audio(audioUrl)
    
    // Store reference to current audio
    currentAudio = audio
    
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl)
      if (currentAudio === audio) {
        currentAudio = null
      }
    }
    
    await audio.play()
  } catch (error) {
    console.error('Error playing audio:', error)
  }
}


const generateInitialGreeting = async () => {
  const greetingText = "Hi, little detective! I'm Curio, your friendly science assistant. We are going to explore the scientific mystery in the image together! What do you find odd in this picture?"
  
  // Add greeting message to chat history
  chatHistory.value.push({
    role: 'assistant',
    content: greetingText,
    time: getCurrentTime()
  })
  
  await scrollToBottom()
  
  // Generate and play audio for the greeting
  await generateAndPlayAudio(greetingText)
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.code === 'Space' && !isRecording.value && !isLoading.value) {
    e.preventDefault()
    startRecording()
  }
}

const handleKeyUp = (e: KeyboardEvent) => {
  if (e.code === 'Space' && isRecording.value) {
    e.preventDefault()
    stopRecording()
  }
}

onMounted(async () => {
  document.addEventListener('keydown', handleKeyDown)
  document.addEventListener('keyup', handleKeyUp)
  
  // Generate initial greeting with audio
  await generateInitialGreeting()
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('keyup', handleKeyUp)
  
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }
})
</script>

<style scoped>
/* Chat Section */
.chat-container {
  width: 100%;
  max-width: 500px;
  height: 80vh;
  background: white;
  border-radius: 25px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Chat Header */
.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  text-align: center;
}

.chat-title {
  margin: 0;
  font-size: 1.8em;
  font-weight: bold;
}

.chat-subtitle {
  margin-top: 5px;
  opacity: 0.9;
  font-size: 1em;
}

/* Chat Messages */
.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f8f9ff;
}

.message {
  margin-bottom: 15px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 20px;
  position: relative;
}

.message.user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 5px;
}

.message.assistant .message-bubble {
  background: white;
  color: #333;
  border: 2px solid #e0e0e0;
  border-bottom-left-radius: 5px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.message-text {
  font-size: 1em;
  line-height: 1.4;
  margin-bottom: 5px;
  text-align: left;
}

.message-time {
  font-size: 0.75em;
  opacity: 0.7;
  text-align: right;
}

/* Welcome Message */
.welcome-message {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.welcome-bubble {
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  padding: 20px;
  border-radius: 20px;
  text-align: center;
  border: 3px solid #ff6b9d;
}

.welcome-text {
  font-size: 1.1em;
  color: #333;
  line-height: 1.5;
}

/* Push-to-Talk Input */
.chat-input-area {
  padding: 20px;
  background: white;
  border-top: 2px solid #f0f0f0;
}

.push-to-talk-container {
  display: flex;
  justify-content: center;
  align-items: center;
}

.push-to-talk-button {
  width: 200px;
  height: 200px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
  position: relative;
  overflow: hidden;
}

.push-to-talk-button:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
}

.push-to-talk-button:active {
  transform: scale(0.95);
}

.push-to-talk-button.recording {
  background: linear-gradient(135deg, #ff6b9d 0%, #c44569 100%);
  animation: pulse 1.5s infinite;
  box-shadow: 0 8px 25px rgba(255, 107, 157, 0.4);
}

.push-to-talk-button.loading {
  background: linear-gradient(135deg, #ffa726 0%, #ff7043 100%);
  cursor: not-allowed;
}

.push-to-talk-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.button-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.mic-icon, .recording-icon, .loading-icon {
  font-size: 3em;
  margin-bottom: 10px;
  display: block;
}

.recording-icon {
  animation: bounce 0.6s infinite alternate;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

.button-text {
  font-size: 1.2em;
  font-weight: bold;
  margin-bottom: 5px;
}

.keyboard-hint {
  font-size: 0.9em;
  opacity: 0.8;
  font-style: italic;
}

@keyframes pulse {
  0% {
    box-shadow: 0 8px 25px rgba(255, 107, 157, 0.4);
  }
  50% {
    box-shadow: 0 8px 35px rgba(255, 107, 157, 0.6);
  }
  100% {
    box-shadow: 0 8px 25px rgba(255, 107, 157, 0.4);
  }
}

@keyframes bounce {
  0% {
    transform: translateY(0);
  }
  100% {
    transform: translateY(-10px);
  }
}

.loading {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive Design */
@media (max-width: 768px) {
  .chat-container {
    height: 55vh;
  }
  
  .chat-header {
    padding: 15px;
  }
  
  .chat-title {
    font-size: 1.5em;
  }
  
  .push-to-talk-button {
    width: 150px;
    height: 150px;
  }
  
  .mic-icon, .recording-icon, .loading-icon {
    font-size: 2.5em;
  }
  
  .button-text {
    font-size: 1em;
  }
  
  .keyboard-hint {
    font-size: 0.8em;
  }
}

/* Scrollbar Styling */
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
}
</style>
