<template>
  <div class="image-selection-container">
    <div class="selection-header">
      <h1 class="selection-title">Choose a Mystery Image!</h1>
      <p class="selection-subtitle">Select an image to explore with Curio!</p>
    </div>
    
    <div class="images-grid">
      <div 
        v-for="(img, index) in images" 
        :key="index"
        class="image-card"
        @click="selectImage(img)"
        :class="{ selected: selectedImage === img.path }"
      >
        <div class="card-frame">
          <img 
            :src="img.path" 
            :alt="img.alt"
            class="preview-image"
          />
          <div class="overlay">
            <div class="overlay-content">
              <span class="icon">🔍</span>
              <!-- <span class="overlay-text">{{ img.name }}</span> -->
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="selection-footer">
      <button 
        @click="handleConfirm" 
        :disabled="!selectedImage"
        class="confirm-button"
      >
        Start Adventure!
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface ImageOption {
  path: string
  alt: string
  name: string
}

const images = ref<ImageOption[]>([
  {
    path: '/imgs/balloon.jpg',
    alt: 'Two girls with pink balloons',
    name: 'Balloon Mystery'
  },
  {
    path: '/imgs/bend.jpg',
    alt: 'Bending Water mystery',
    name: 'Bending Water Mystery'
  },
  {
    path: '/imgs/pepper.jpg',
    alt: 'Pepper mystery',
    name: 'Pepper Mystery'
  }
])

const selectedImage = ref<string>('')

const selectImage = (img: ImageOption) => {
  selectedImage.value = img.path
}

const handleConfirm = () => {
  if (selectedImage.value) {
    // Navigate to /chat with image path as query parameter
    router.push({
      path: '/chat',
      query: { image: selectedImage.value }
    })
  }
}
</script>

<style scoped>
.image-selection-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: 'Comic Sans MS', cursive, sans-serif;
}

.selection-header {
  text-align: center;
  margin-bottom: 40px;
}

.selection-title {
  font-size: 3em;
  color: white;
  margin-bottom: 10px;
  text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.3);
}

.selection-subtitle {
  font-size: 1.3em;
  color: rgba(255, 255, 255, 0.9);
  font-weight: bold;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  max-width: 900px;
  width: 100%;
  margin-bottom: 40px;
}

.image-card {
  cursor: pointer;
  transition: transform 0.3s ease;
}

.image-card:hover {
  transform: translateY(-10px);
}

.image-card.selected {
  transform: translateY(-10px);
}

.card-frame {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  border: 4px solid transparent;
  transition: all 0.3s ease;
}

.image-card.selected .card-frame {
  border-color: #ff6b9d;
  box-shadow: 0 15px 40px rgba(255, 107, 157, 0.5);
}

.preview-image {
  width: 100%;
  height: 250px;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.image-card:hover .preview-image {
  transform: scale(1.05);
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(to bottom, rgba(102, 126, 234, 0.1), rgba(255, 107, 157, 0.7));
  display: flex;
  align-items: flex-end;
  padding: 20px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.image-card:hover .overlay,
.image-card.selected .overlay {
  opacity: 1;
}

.overlay-content {
  display: flex;
  align-items: center;
  gap: 10px;
  color: white;
  font-size: 1.1em;
  font-weight: bold;
}

.icon {
  font-size: 1.5em;
}

.selection-footer {
  display: flex;
  justify-content: center;
}

.confirm-button {
  background: linear-gradient(135deg, #ff6b9d 0%, #c44569 100%);
  color: white;
  border: none;
  padding: 20px 50px;
  border-radius: 50px;
  font-size: 1.5em;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 25px rgba(255, 107, 157, 0.4);
  font-family: 'Comic Sans MS', cursive, sans-serif;
}

.confirm-button:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 12px 35px rgba(255, 107, 157, 0.6);
}

.confirm-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* Responsive Design */
@media (max-width: 768px) {
  .selection-title {
    font-size: 2em;
  }
  
  .selection-subtitle {
    font-size: 1em;
  }
  
  .images-grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .preview-image {
    height: 200px;
  }
  
  .confirm-button {
    padding: 15px 40px;
    font-size: 1.2em;
  }
}
</style>

