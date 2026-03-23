// imageCompress.js — 前端图片压缩工具
// 宽/高超过 maxWidth 时等比缩放，输出 JPEG Base64 data URL

const MAX_FILE_SIZE = 10 * 1024 * 1024  // 10MB（单张上限，与 Qwen VL 要求一致）
const MAX_WIDTH = 2048                   // 超过此尺寸时等比缩放
const JPEG_QUALITY = 0.85               // JPEG 压缩质量

/**
 * 压缩图片并返回 Base64 data URL
 * @param {File} file - 图片文件
 * @returns {Promise<string>} data URL（data:image/...;base64,...）
 * @throws {Error} 文件过大或格式不支持时抛出
 */
export async function compressImage(file) {
  if (file.size > MAX_FILE_SIZE) {
    throw new Error(`图片大小不能超过 10MB（当前 ${(file.size / 1024 / 1024).toFixed(1)}MB）`)
  }

  const supportedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
  if (!supportedTypes.includes(file.type)) {
    throw new Error('仅支持 JPG、PNG、WebP 格式')
  }

  return new Promise((resolve, reject) => {
    const img = new Image()
    const objectUrl = URL.createObjectURL(file)

    img.onload = () => {
      URL.revokeObjectURL(objectUrl)

      const { width: origW, height: origH } = img
      let targetW = origW
      let targetH = origH

      // 等比缩放：长边超过 MAX_WIDTH 时缩小
      if (origW > MAX_WIDTH || origH > MAX_WIDTH) {
        const ratio = MAX_WIDTH / Math.max(origW, origH)
        targetW = Math.round(origW * ratio)
        targetH = Math.round(origH * ratio)
      }

      const canvas = document.createElement('canvas')
      canvas.width = targetW
      canvas.height = targetH
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, targetW, targetH)

      // PNG 转 JPEG（透明背景填白）以减小体积
      if (file.type === 'image/png') {
        const imageData = ctx.getImageData(0, 0, targetW, targetH)
        const data = imageData.data
        for (let i = 3; i < data.length; i += 4) {
          if (data[i] < 255) {
            // 半透明像素：与白色背景合成
            const alpha = data[i] / 255
            data[i - 3] = Math.round(data[i - 3] * alpha + 255 * (1 - alpha))
            data[i - 2] = Math.round(data[i - 2] * alpha + 255 * (1 - alpha))
            data[i - 1] = Math.round(data[i - 1] * alpha + 255 * (1 - alpha))
            data[i] = 255
          }
        }
        ctx.putImageData(imageData, 0, 0)
      }

      resolve(canvas.toDataURL('image/jpeg', JPEG_QUALITY))
    }

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('图片加载失败，请重新选择'))
    }

    img.src = objectUrl
  })
}
