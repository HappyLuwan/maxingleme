// pages/result/result.js
const api = require('../../utils/api')

Page({
  data: {
    roast: {
      roastId: '',
      content: '',
      style: '',
      styleName: '',
      styleEmoji: ''
    },
    templates: [
      { key: 'chat', name: '聊天截图风', icon: '💬' },
      { key: 'attack', name: '暴击语录风', icon: '💥' },
      { key: 'poster', name: '海报文艺风', icon: '📜' },
      { key: 'punch', name: '金句海报风', icon: '⚡️' }
    ],
    selectedTemplate: 'chat',
    generatingCard: false,
    cardImageUrl: ''
  },

  onLoad(options) {
    // 从本地缓存拿骂醒数据（首页存的）
    const roast = wx.getStorageSync('lastRoast')
    if (roast && roast.roastId === options.roastId) {
      // 一句话暴击默认选金句海报模板，其他保持 chat
      const defaultTpl = roast.style === 'yiju' ? 'punch' : 'chat'
      this.setData({ roast, selectedTemplate: defaultTpl })
    } else {
      wx.showToast({ title: '数据丢失，请重新骂醒', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1500)
    }
  },

  /**
   * 选择卡片模板
   */
  onSelectTemplate(e) {
    const key = e.currentTarget.dataset.key
    this.setData({ selectedTemplate: key })
    wx.vibrateShort({ type: 'light' })
  },

  /**
   * 生成卡片
   */
  onGenerateCard() {
    if (!this.data.roast.roastId) {
      wx.showToast({ title: '骂醒记录已失效', icon: 'none' })
      return
    }
    this.setData({ generatingCard: true, cardImageUrl: '' })
    wx.showLoading({ title: '生成中...', mask: true })

    api.generateCard(this.data.roast.roastId, this.data.selectedTemplate).then((result) => {
      wx.hideLoading()
      // 优先用 Base64（云托管零配置就能看图），否则降级到 http URL
      const imgSrc = result.imageBase64 || api.fullImageUrl(result.imageUrl)
      this.setData({
        generatingCard: false,
        cardImageUrl: imgSrc
      })
      wx.vibrateShort({ type: 'medium' })
    }).catch((err) => {
      wx.hideLoading()
      this.setData({ generatingCard: false })
      wx.showModal({
        title: '生成失败',
        content: err.message || '请稍后重试',
        showCancel: false
      })
    })
  },

  /**
   * 保存图片到相册
   * - 如果是 dataURL（base64），先写到临时文件再保存
   * - 如果是 http URL，走 downloadFile
   */
  onSaveImage() {
    if (!this.data.cardImageUrl) return
    const src = this.data.cardImageUrl
    if (src.startsWith('data:image')) {
      this.saveBase64Image(src)
    } else {
      this.saveRemoteImage(src)
    }
  },

  saveBase64Image(dataUrl) {
    wx.showLoading({ title: '保存中...', mask: true })
    const base64 = dataUrl.replace(/^data:image\/\w+;base64,/, '')
    const filePath = `${wx.env.USER_DATA_PATH}/mxlm_card_${Date.now()}.png`
    const fs = wx.getFileSystemManager()
    fs.writeFile({
      filePath,
      data: base64,
      encoding: 'base64',
      success: () => {
        wx.saveImageToPhotosAlbum({
          filePath,
          success: () => {
            wx.hideLoading()
            wx.showToast({ title: '已保存到相册', icon: 'success' })
          },
          fail: (err) => {
            wx.hideLoading()
            if (err.errMsg.indexOf('auth deny') > -1 || err.errMsg.indexOf('authorize') > -1) {
              wx.showModal({
                title: '需要相册权限',
                content: '请在设置中开启保存到相册的权限',
                confirmText: '去设置',
                success: (m) => { if (m.confirm) wx.openSetting() }
              })
            } else {
              wx.showToast({ title: '保存失败', icon: 'none' })
            }
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '写入临时文件失败', icon: 'none' })
      }
    })
  },

  saveRemoteImage(url) {
    wx.showLoading({ title: '下载中...' })
    wx.downloadFile({
      url,
      success: (res) => {
        wx.hideLoading()
        if (res.statusCode !== 200) {
          wx.showToast({ title: '下载失败', icon: 'none' })
          return
        }
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => {
            wx.showToast({ title: '已保存到相册', icon: 'success' })
          },
          fail: (err) => {
            if (err.errMsg.indexOf('auth deny') > -1 || err.errMsg.indexOf('authorize') > -1) {
              wx.showModal({
                title: '需要相册权限',
                content: '请在设置中开启保存到相册的权限',
                confirmText: '去设置',
                success: (m) => { if (m.confirm) wx.openSetting() }
              })
            } else {
              wx.showToast({ title: '保存失败', icon: 'none' })
            }
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '下载失败', icon: 'none' })
      }
    })
  },

  /**
   * 再骂一次
   */
  onAgain() {
    wx.navigateBack()
  },

  /**
   * 分享给朋友（带卡片图作为封面）
   * 注：wx.onShareAppMessage.imageUrl 不支持 base64，如果是 base64 则不传 imageUrl，由微信默认截页面
   */
  onShareAppMessage() {
    const src = this.data.cardImageUrl
    const isHttp = src && src.startsWith('http')
    return {
      title: '我被 AI 一句话骂醒了：' + this.truncate(this.data.roast.content, 30),
      path: '/pages/index/index',
      imageUrl: isHttp ? src : ''
    }
  },

  /**
   * 分享到朋友圈
   */
  onShareTimeline() {
    const src = this.data.cardImageUrl
    const isHttp = src && src.startsWith('http')
    return {
      title: this.truncate(this.data.roast.content, 30) + ' —— 骂醒了么',
      query: '',
      imageUrl: isHttp ? src : ''
    }
  },

  truncate(str, len) {
    if (!str) return ''
    return str.length > len ? str.substring(0, len) + '...' : str
  }
})
