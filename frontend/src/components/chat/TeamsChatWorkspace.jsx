import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  MessageSquare,
  Users,
  Search,
  Plus,
  Send,
  Smile,
  Paperclip,
  Pin,
  Trash2,
  Reply,
  Edit2,
  Info,
  Phone,
  Video,
  CheckCheck,
  X,
  Hash,
  Calendar,
  FileText,
  Download,
  UserPlus,
  UserMinus,
  ArrowLeft,
  Loader2,
  Image as ImageIcon,
  Check,
} from 'lucide-react';
import { chatService } from '../../services/chatService';
import '../../styles/teamsChat.css';

const QUICK_REPLIES = [
  'Working on it right away! 👍',
  'Please check the latest updates.',
  'Approved, please proceed.',
  'Let us connect in a quick meeting 📞',
  'Thanks for the update! 🎉',
  'Kindly share your attendance update.',
];

const EMOJIS = ['👍', '❤️', '👏', '🎉', '🚀', '😊', '🔥', '✅'];

const formatChatTime = (isoString) => {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    const now = new Date();
    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear();
    if (isToday) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday =
      d.getDate() === yesterday.getDate() &&
      d.getMonth() === yesterday.getMonth() &&
      d.getFullYear() === yesterday.getFullYear();
    if (isYesterday) {
      return 'Yesterday';
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
};

export default function TeamsChatWorkspace() {
  const [searchParams] = useSearchParams();
  const queryTeam = searchParams.get('team');
  const queryUser = searchParams.get('user');

  // Stored current user profile
  const currentUser = (() => {
    try {
      return JSON.parse(localStorage.getItem('arshith_user')) || {};
    } catch {
      return {};
    }
  })();
  const userRole = localStorage.getItem('arshith_role') || currentUser.role || 'employee';
  const isAdmin = userRole.toLowerCase() === 'admin';
  const myPrimaryId = currentUser.employeeId || currentUser.employee_id || currentUser.id || (isAdmin ? 'ADM-001' : 'employee');

  // Data states
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [teams, setTeams] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);

  // UI & Filter states
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'direct', 'teams', 'unread'
  const [searchQuery, setSearchQuery] = useState('');
  const [inputMessage, setInputMessage] = useState('');
  const [replyingTo, setReplyingTo] = useState(null);
  const [editingMessage, setEditingMessage] = useState(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isNewChatOpen, setIsNewChatOpen] = useState(false);
  const [typingUsers, setTypingUsers] = useState({});

  // Attachments & Lightbox
  const [attachedFile, setAttachedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [lightboxImage, setLightboxImage] = useState(null);

  // Group creation modal state
  const [modalTab, setModalTab] = useState('direct'); // 'direct' or 'group'
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const [selectedGroupMembers, setSelectedGroupMembers] = useState([]);
  const [isCreatingGroup, setIsCreatingGroup] = useState(false);
  const [groupMemberSearch, setGroupMemberSearch] = useState('');

  // Add member dropdown state
  const [showAddMemberSelect, setShowAddMemberSelect] = useState(false);
  const [selectedAddMemberId, setSelectedAddMemberId] = useState('');

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  // Scroll to bottom of message list
  const scrollToBottom = (smooth = true) => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
    }
  };

  // Load conversations and contacts
  const loadInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [convsData, contactsData, teamsData] = await Promise.all([
        chatService.getConversations(),
        chatService.getContacts(),
        chatService.getTeams(),
      ]);

      const convList = Array.isArray(convsData) ? convsData : [];
      setConversations(convList);
      setContacts(Array.isArray(contactsData) ? contactsData : []);
      setTeams(Array.isArray(teamsData) ? teamsData : []);

      // Determine initial active conversation
      let selected = null;
      if (queryTeam) {
        selected = convList.find(
          (c) => c.type === 'team' && (c.target_id === queryTeam || c.title.toLowerCase() === queryTeam.toLowerCase())
        );
      } else if (queryUser) {
        selected = convList.find(
          (c) => c.type === 'direct' && c.target_id.toLowerCase() === queryUser.toLowerCase()
        );
        if (!selected) {
          const foundContact = (contactsData || []).find(
            (ct) => ct.id === queryUser || ct.employee_id === queryUser || ct.email === queryUser
          );
          if (foundContact) {
            selected = {
              conversation_id: `direct_${foundContact.id}`,
              type: 'direct',
              target_id: foundContact.id,
              title: foundContact.name,
              subtitle: `${foundContact.designation || 'Staff'} • ${foundContact.department || 'Operations'}`,
              avatar: foundContact.avatar || 'U',
              is_online: foundContact.is_online,
              last_message: '',
              unread_count: 0,
            };
          }
        }
      }

      // Default to first conversation
      if (!selected && convList.length > 0) {
        selected = convList[0];
      }
      setActiveConversation(selected);
    } catch (err) {
      console.error('Failed to load chat data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [queryTeam, queryUser]);

  // Load messages for currently active conversation
  const loadMessages = useCallback(async (conv) => {
    if (!conv) return;
    try {
      const msgs = await chatService.getMessages(conv.type, conv.target_id);
      setMessages(msgs || []);
      // Clear unread badge locally
      setConversations((prev) =>
        prev.map((c) => (c.conversation_id === conv.conversation_id ? { ...c, unread_count: 0 } : c))
      );
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // When active conversation changes, fetch its messages
  useEffect(() => {
    if (activeConversation) {
      loadMessages(activeConversation);
      setEditingMessage(null);
      setReplyingTo(null);
      setAttachedFile(null);
      setTimeout(() => scrollToBottom(false), 80);
    }
  }, [activeConversation, loadMessages]);

  // WebSocket real-time subscription & Polling fallback
  useEffect(() => {
    const handleWsEvent = (event) => {
      if (event.type === 'new_message' && event.message) {
        const msg = event.message;
        // Check if message belongs to currently open conversation
        if (activeConversation) {
          const isCurrentTeam =
            activeConversation.type === 'team' &&
            msg.chat_type === 'team' &&
            (msg.team_id === activeConversation.target_id ||
              msg.target_id === activeConversation.target_id ||
              (activeConversation.title && msg.team_name && activeConversation.title.toLowerCase() === msg.team_name.toLowerCase()));
          const isCurrentDirect =
            activeConversation.type === 'direct' &&
            msg.chat_type === 'direct' &&
            (msg.sender_id.toLowerCase() === activeConversation.target_id.toLowerCase() ||
              msg.receiver_id.toLowerCase() === activeConversation.target_id.toLowerCase());

          if (isCurrentTeam || isCurrentDirect) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === msg.id)) return prev;
              return [...prev, msg];
            });
            setTimeout(() => scrollToBottom(true), 50);
          }
        }

        // Update conversation preview snippet
        setConversations((prev) =>
          prev.map((c) => {
            const matches =
              (c.type === 'team' &&
                msg.chat_type === 'team' &&
                (c.target_id === (msg.team_id || msg.target_id) ||
                  (c.title && msg.team_name && c.title.toLowerCase() === msg.team_name.toLowerCase()))) ||
              (c.type === 'direct' &&
                msg.chat_type === 'direct' &&
                (c.target_id.toLowerCase() === msg.sender_id.toLowerCase() ||
                  c.target_id.toLowerCase() === msg.receiver_id.toLowerCase()));
            if (matches) {
              return {
                ...c,
                last_message: msg.content || (msg.attachments?.length ? 'Shared an attachment' : ''),
                last_message_sender: msg.sender_name,
                last_message_at: msg.created_at,
                unread_count: activeConversation?.target_id === c.target_id ? 0 : c.unread_count + 1,
              };
            }
            return c;
          })
        );
      } else if (event.type === 'message_edited') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === event.message_id
              ? { ...m, content: event.content, is_edited: true, updated_at: event.updated_at }
              : m
          )
        );
      } else if (event.type === 'reaction_updated') {
        setMessages((prev) =>
          prev.map((m) => (m.id === event.message_id ? { ...m, reactions: event.reactions } : m))
        );
      } else if (event.type === 'pin_updated') {
        setMessages((prev) =>
          prev.map((m) => (m.id === event.message_id ? { ...m, is_pinned: event.is_pinned } : m))
        );
      } else if (event.type === 'message_deleted') {
        setMessages((prev) => prev.filter((m) => m.id !== event.message_id));
      } else if (event.type === 'new_team' && event.team) {
        setTeams((prev) => [event.team, ...prev]);
        loadInitialData();
      } else if (event.type === 'typing') {
        if (activeConversation && event.target_id === activeConversation.target_id.toLowerCase()) {
          setTypingUsers((prev) => ({
            ...prev,
            [event.sender_name]: event.is_typing,
          }));
          if (event.is_typing) {
            setTimeout(() => {
              setTypingUsers((prev) => {
                const next = { ...prev };
                delete next[event.sender_name];
                return next;
              });
            }, 3000);
          }
        }
      }
    };

    const cleanupWs = chatService.connectWebSocket(handleWsEvent);

    // Light polling interval (every 4 seconds) to ensure synchronization
    const pollInterval = setInterval(() => {
      if (activeConversation) {
        chatService
          .getMessages(activeConversation.type, activeConversation.target_id)
          .then((fresh) => {
            if (Array.isArray(fresh)) {
              setMessages((prev) => {
                if (
                  fresh.length !== prev.length ||
                  fresh[fresh.length - 1]?.id !== prev[prev.length - 1]?.id ||
                  fresh.some((m, idx) => m.content !== prev[idx]?.content)
                ) {
                  return fresh;
                }
                return prev;
              });
            }
          })
          .catch(() => {});
      }
    }, 4000);

    return () => {
      cleanupWs();
      clearInterval(pollInterval);
    };
  }, [activeConversation, loadInitialData]);

  // Handle typing notification
  const handleInputChange = (e) => {
    setInputMessage(e.target.value);
    if (activeConversation) {
      chatService.sendTyping(activeConversation.type, activeConversation.target_id, true);
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = setTimeout(() => {
        chatService.sendTyping(activeConversation.type, activeConversation.target_id, false);
      }, 1500);
    }
  };

  // File upload selection
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      alert('File exceeds the maximum limit of 10MB.');
      return;
    }

    try {
      setIsUploading(true);
      const res = await chatService.uploadAttachment(file);
      setAttachedFile(res);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to upload attachment.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Start editing a message
  const handleStartEdit = (msg) => {
    setEditingMessage(msg);
    setInputMessage(msg.content);
    setReplyingTo(null);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  // Cancel edit mode
  const handleCancelEdit = () => {
    setEditingMessage(null);
    setInputMessage('');
  };

  // Send message or Save Edit
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const cleanContent = inputMessage.trim();
    if ((!cleanContent && !attachedFile) || !activeConversation || isSending) return;

    // Handle Edit Mode
    if (editingMessage) {
      try {
        setIsSending(true);
        await chatService.editMessage(editingMessage.id, cleanContent);
        setMessages((prev) =>
          prev.map((m) => (m.id === editingMessage.id ? { ...m, content: cleanContent, is_edited: true } : m))
        );
        setEditingMessage(null);
        setInputMessage('');
      } catch (err) {
        alert(err.response?.data?.detail || 'Failed to edit message.');
      } finally {
        setIsSending(false);
      }
      return;
    }

    // Normal Send Mode
    try {
      setIsSending(true);
      setInputMessage('');
      const replyData = replyingTo
        ? {
            id: replyingTo.id,
            sender_name: replyingTo.sender_name,
            content_snippet: replyingTo.content.substring(0, 80),
          }
        : null;

      setReplyingTo(null);
      const toSendAttachment = attachedFile ? [attachedFile] : [];
      setAttachedFile(null);

      const created = await chatService.sendMessage({
        chatType: activeConversation.type,
        targetId: activeConversation.target_id,
        content: cleanContent || (toSendAttachment.length ? `Shared: ${toSendAttachment[0].filename}` : ''),
        attachments: toSendAttachment,
        replyTo: replyData,
      });

      setMessages((prev) => [...prev, created]);
      setTimeout(() => scrollToBottom(true), 50);

      // Refresh conversations list snippet
      setConversations((prev) =>
        prev.map((c) =>
          c.conversation_id === activeConversation.conversation_id
            ? {
                ...c,
                last_message: cleanContent || (toSendAttachment.length ? toSendAttachment[0].filename : ''),
                last_message_at: new Date().toISOString(),
              }
            : c
        )
      );
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      setIsSending(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  // Keyboard shortcut: Enter to send, Shift+Enter for newline, Esc to cancel edit
  const handleKeyDown = (e) => {
    if (e.key === 'Escape' && editingMessage) {
      handleCancelEdit();
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Quick reaction toggle
  const handleToggleReaction = async (messageId, emoji) => {
    try {
      const res = await chatService.toggleReaction(messageId, emoji);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, reactions: res.reactions } : m))
      );
    } catch (err) {
      console.error('Failed to toggle reaction:', err);
    }
  };

  // Toggle pin
  const handleTogglePin = async (messageId) => {
    try {
      const res = await chatService.togglePin(messageId);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, is_pinned: res.is_pinned } : m))
      );
    } catch (err) {
      console.error('Failed to pin message:', err);
    }
  };

  // Delete message
  const handleDeleteMessage = async (messageId) => {
    if (window.confirm('Delete this message for everyone?')) {
      try {
        await chatService.deleteMessage(messageId);
        setMessages((prev) => prev.filter((m) => m.id !== messageId));
      } catch (err) {
        console.error('Failed to delete message:', err);
      }
    }
  };

  // Start new conversation from modal (Contact)
  const handleStartChatWithContact = (contact) => {
    const existing = conversations.find(
      (c) => c.type === 'direct' && c.target_id.toLowerCase() === contact.id.toLowerCase()
    );
    if (existing) {
      setActiveConversation(existing);
    } else {
      const newConv = {
        conversation_id: `direct_${contact.id}`,
        type: 'direct',
        target_id: contact.id,
        title: contact.name,
        subtitle: `${contact.designation || 'Staff'} • ${contact.department || 'Operations'}`,
        avatar: contact.avatar || 'U',
        is_online: contact.is_online,
        last_message: '',
        unread_count: 0,
      };
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversation(newConv);
    }
    setIsNewChatOpen(false);
  };

  // Select team channel
  const handleSelectTeamChannel = (team) => {
    const existing = conversations.find((c) => c.type === 'team' && c.target_id === String(team.id));
    if (existing) {
      setActiveConversation(existing);
    } else {
      const newConv = {
        conversation_id: `team_${team.id}`,
        type: 'team',
        target_id: String(team.id),
        title: team.name,
        subtitle: `${team.department || 'Company'} • ${team.member_count || 0} members`,
        avatar: '#',
        last_message: '',
        unread_count: 0,
      };
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversation(newConv);
    }
    setIsNewChatOpen(false);
  };

  // Create team group channel
  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) {
      alert('Please enter a team group name.');
      return;
    }

    try {
      setIsCreatingGroup(true);
      const created = await chatService.createGroup({
        name: newGroupName.trim(),
        description: newGroupDescription.trim(),
        memberIds: selectedGroupMembers,
      });

      const newConv = {
        conversation_id: `team_${created.id}`,
        type: 'team',
        target_id: String(created.id),
        title: created.name,
        subtitle: `Custom Group • ${created.members?.length || 1} members`,
        avatar: '#',
        last_message: 'Group created',
        last_message_at: created.created_at,
        unread_count: 0,
      };
      setTeams((prev) => [created, ...prev]);
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversation(newConv);

      setIsNewChatOpen(false);
      setNewGroupName('');
      setNewGroupDescription('');
      setSelectedGroupMembers([]);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create group.');
    } finally {
      setIsCreatingGroup(false);
    }
  };

  // Toggle group member selection for new group
  const handleToggleMemberSelection = (id) => {
    setSelectedGroupMembers((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  // Add member to current group
  const handleAddMemberToCurrentGroup = async () => {
    if (!selectedAddMemberId || !activeConversation || activeConversation.type !== 'team') return;
    try {
      const res = await chatService.addGroupMember(activeConversation.target_id, selectedAddMemberId);
      setTeams((prev) =>
        prev.map((t) =>
          String(t.id) === activeConversation.target_id
            ? { ...t, members: res.members, member_count: res.members.length }
            : t
        )
      );
      setSelectedAddMemberId('');
      setShowAddMemberSelect(false);
      loadMessages(activeConversation);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add member.');
    }
  };

  // Remove member or leave group
  const handleRemoveMemberFromGroup = async (userId) => {
    if (!activeConversation || activeConversation.type !== 'team') return;
    const isSelf = userId.toLowerCase() === myPrimaryId.toLowerCase();
    const promptMsg = isSelf
      ? 'Are you sure you want to leave this group channel?'
      : `Remove employee ${userId} from this group?`;

    if (!window.confirm(promptMsg)) return;

    try {
      const res = await chatService.removeGroupMember(activeConversation.target_id, userId);
      if (isSelf) {
        setConversations((prev) => prev.filter((c) => c.conversation_id !== activeConversation.conversation_id));
        setActiveConversation(null);
      } else {
        setTeams((prev) =>
          prev.map((t) =>
            String(t.id) === activeConversation.target_id
              ? { ...t, members: res.members, member_count: res.members.length }
              : t
          )
        );
        loadMessages(activeConversation);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to remove member.');
    }
  };

  // Filter conversations
  const filteredConversations = conversations.filter((c) => {
    const matchesTab =
      activeTab === 'all' ||
      (activeTab === 'direct' && c.type === 'direct') ||
      (activeTab === 'teams' && c.type === 'team') ||
      (activeTab === 'unread' && (c.unread_count || 0) > 0);
    const matchesQuery =
      !searchQuery ||
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.last_message && c.last_message.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesTab && matchesQuery;
  });

  const pinnedMessage = messages.find((m) => m.is_pinned);
  const typingNames = Object.keys(typingUsers).filter((name) => typingUsers[name]);

  // Active channel team object if active is a team
  const currentTeamObj =
    activeConversation?.type === 'team'
      ? teams.find((t) => String(t.id) === activeConversation.target_id)
      : null;

  // List of shared attachments in the active conversation
  const sharedAttachments = messages
    .flatMap((m) => m.attachments || [])
    .filter(Boolean);

  return (
    <div className="teams-chat-container animate-fade-in">
      {/* Hidden File Input for Attachments */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleFileSelect}
        accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.docx,.doc,.xlsx,.xls,.txt,.csv,.zip"
      />

      {/* 1. Left Icon Rail (Teams Signature Rail) */}
      <div className="teams-app-rail">
        <div className="teams-rail-logo" title="Arshith Connect Teams">
          T
        </div>

        <button
          type="button"
          className={`teams-rail-btn ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
          title="All Chats"
        >
          <MessageSquare size={20} />
          <span>Chat</span>
        </button>

        <button
          type="button"
          className={`teams-rail-btn ${activeTab === 'teams' ? 'active' : ''}`}
          onClick={() => setActiveTab('teams')}
          title="Teams & Channels"
        >
          <Users size={20} />
          <span>Teams</span>
        </button>

        <button
          type="button"
          className="teams-rail-btn"
          onClick={() => {
            setModalTab('direct');
            setIsNewChatOpen(true);
          }}
          title="Start New Chat"
        >
          <Plus size={20} />
          <span>New</span>
        </button>
      </div>

      {/* 2. Middle Conversations & Channels List */}
      <div className="teams-conversations-sidebar">
        {/* Header with Title and "New Chat" Button */}
        <div className="teams-sidebar-top">
          <div className="teams-sidebar-header-row">
            <h2 className="teams-sidebar-title">
              <span>Teams Chat</span>
            </h2>
            <button
              type="button"
              className="teams-new-chat-btn"
              onClick={() => {
                setModalTab('direct');
                setIsNewChatOpen(true);
              }}
              title="Compose message to employee or team"
            >
              <Plus size={14} />
              <span>New</span>
            </button>
          </div>

          {/* Search Box */}
          <div className="teams-search-box">
            <Search size={15} className="teams-search-icon" />
            <input
              type="text"
              placeholder="Search chat or teams..."
              className="teams-search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                className="teams-search-clear"
                onClick={() => setSearchQuery('')}
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Filter Tabs: All, Direct, Channels, Unread */}
        <div className="teams-filter-tabs">
          <button
            type="button"
            className={`teams-filter-tab ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            All
          </button>
          <button
            type="button"
            className={`teams-filter-tab ${activeTab === 'direct' ? 'active' : ''}`}
            onClick={() => setActiveTab('direct')}
          >
            Direct
          </button>
          <button
            type="button"
            className={`teams-filter-tab ${activeTab === 'teams' ? 'active' : ''}`}
            onClick={() => setActiveTab('teams')}
          >
            Channels
          </button>
          <button
            type="button"
            className={`teams-filter-tab ${activeTab === 'unread' ? 'active' : ''}`}
            onClick={() => setActiveTab('unread')}
          >
            Unread
          </button>
        </div>

        {/* Scrollable Conversation List */}
        <div className="teams-conversations-list">
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '32px 16px', color: '#64748b', fontSize: '0.85rem' }}>
              <Loader2 className="animate-spin" size={20} style={{ margin: '0 auto 8px auto', color: '#0d9488' }} />
              Loading conversations...
            </div>
          ) : filteredConversations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 16px', color: '#94a3b8', fontSize: '0.82rem' }}>
              No conversations found. Click <strong>New</strong> to start chatting!
            </div>
          ) : (
            filteredConversations.map((c) => {
              const isSelected = activeConversation?.conversation_id === c.conversation_id;
              return (
                <div
                  key={c.conversation_id}
                  className={`teams-conv-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => setActiveConversation(c)}
                >
                  <div className="teams-avatar-wrap">
                    {c.type === 'team' ? (
                      <div className="teams-avatar team">
                        <Hash size={18} />
                      </div>
                    ) : (
                      <>
                        <div className={`teams-avatar ${c.avatar === 'A' ? 'admin' : 'employee'}`}>
                          {c.avatar || 'U'}
                        </div>
                        <div className={`teams-presence-dot ${c.is_online ? 'online' : 'offline'}`} />
                      </>
                    )}
                  </div>

                  <div className="teams-conv-content">
                    <div className="teams-conv-row">
                      <span className="teams-conv-title">{c.title}</span>
                      {c.last_message_at && (
                        <span className="teams-conv-time">
                          {formatChatTime(c.last_message_at)}
                        </span>
                      )}
                    </div>
                    <div className="teams-conv-row">
                      <span className="teams-conv-snippet">
                        {c.last_message_sender ? `${c.last_message_sender}: ` : ''}
                        {c.last_message || 'No messages yet'}
                      </span>
                      {c.unread_count > 0 && (
                        <span className="teams-unread-badge">
                          {c.unread_count > 99 ? '99+' : c.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 3. Center Main Chat Window */}
      {activeConversation ? (
        <div className="teams-main-chat">
          {/* Chat Header */}
          <div className="teams-chat-header">
            <div className="teams-chat-header-info">
              <div className="teams-avatar-wrap">
                {activeConversation.type === 'team' ? (
                  <div className="teams-avatar team">
                    <Hash size={20} />
                  </div>
                ) : (
                  <>
                    <div className={`teams-avatar ${activeConversation.avatar === 'A' ? 'admin' : 'employee'}`}>
                      {activeConversation.avatar || 'U'}
                    </div>
                    <div className={`teams-presence-dot ${activeConversation.is_online ? 'online' : 'offline'}`} />
                  </>
                )}
              </div>
              <div>
                <div className="teams-chat-header-title">{activeConversation.title}</div>
                <div className="teams-chat-header-subtitle">
                  {activeConversation.type === 'team'
                    ? activeConversation.subtitle
                    : activeConversation.is_online
                    ? 'Active Now'
                    : 'Offline'}
                </div>
              </div>
            </div>

            <div className="teams-chat-header-actions">
              <button
                type="button"
                className="teams-header-btn"
                onClick={() => alert(`Starting voice call with ${activeConversation.title}...`)}
                title="Voice Call"
              >
                <Phone size={17} />
              </button>
              <button
                type="button"
                className="teams-header-btn"
                onClick={() => alert(`Starting video meeting with ${activeConversation.title}...`)}
                title="Video Call"
              >
                <Video size={17} />
              </button>
              <button
                type="button"
                className={`teams-header-btn ${isDetailsOpen ? 'active' : ''}`}
                onClick={() => setIsDetailsOpen(!isDetailsOpen)}
                title="Conversation Details"
              >
                <Info size={17} />
              </button>
            </div>
          </div>

          {/* Pinned Message Banner if Any */}
          {pinnedMessage && (
            <div className="teams-pinned-banner">
              <Pin size={14} color="#0d9488" />
              <div style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <strong>Pinned by {pinnedMessage.sender_name}:</strong> {pinnedMessage.content}
              </div>
              <button
                type="button"
                className="teams-action-icon-btn"
                onClick={() => handleTogglePin(pinnedMessage.id)}
                title="Unpin"
              >
                <X size={13} />
              </button>
            </div>
          )}

          {/* Messages Scroll Area */}
          <div className="teams-messages-area">
            {messages.length === 0 ? (
              <div className="teams-empty-messages">
                <div className="teams-empty-messages-icon">
                  {activeConversation.type === 'team' ? <Hash size={40} /> : <MessageSquare size={40} />}
                </div>
                <h3>Welcome to #{activeConversation.title}!</h3>
                <p>This is the start of your real-time conversation. Send a message to get started.</p>
              </div>
            ) : (
              messages.map((msg) => {
                const isMine =
                  msg.sender_id.toLowerCase() === myPrimaryId.toLowerCase() ||
                  (isAdmin && ['adm-001', 'admin', 'admin@arshith.com'].includes(msg.sender_id.toLowerCase()));

                return (
                  <div
                    key={msg.id}
                    className={`teams-msg-row ${isMine ? 'outgoing' : 'incoming'} ${
                      msg.sender_role === 'system' ? 'system-msg-row' : ''
                    }`}
                  >
                    {!isMine && msg.sender_role !== 'system' && (
                      <div className="teams-msg-avatar">
                        {msg.sender_avatar || msg.sender_name?.[0] || 'U'}
                      </div>
                    )}

                    <div className="teams-msg-body">
                      {msg.sender_role === 'system' ? (
                        <div style={{ textAlign: 'center', color: '#64748b', fontSize: '0.78rem', margin: '4px 0', fontStyle: 'italic' }}>
                          ⚙️ {msg.content}
                        </div>
                      ) : (
                        <>
                          <div className="teams-msg-header">
                            <span className="teams-msg-sender">{msg.sender_name}</span>
                            {msg.sender_role === 'admin' ? (
                              <span className="teams-role-pill admin">ADMIN</span>
                            ) : (
                              <span className="teams-role-pill employee">STAFF</span>
                            )}
                            <span className="teams-msg-timestamp">
                              {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            {msg.is_edited && <span className="teams-msg-edited-tag">(edited)</span>}
                            {msg.is_pinned && <Pin size={12} color="#0d9488" />}
                          </div>

                          {/* Quoted Reply if any */}
                          {msg.reply_to && (
                            <div className="teams-quote-box">
                              <div className="teams-quote-author">{msg.reply_to.sender_name}</div>
                              <div className="teams-quote-text">{msg.reply_to.content_snippet}</div>
                            </div>
                          )}

                          {/* Main Message Bubble */}
                          <div className="teams-msg-bubble">
                            {msg.content}

                            {/* Render Attachments */}
                            {msg.attachments && msg.attachments.length > 0 && (
                              <div className="teams-attachment-container">
                                {msg.attachments.map((att, aIdx) =>
                                  att.is_image ? (
                                    <div
                                      key={aIdx}
                                      className="teams-attachment-img-wrap"
                                      onClick={() => setLightboxImage(att.url)}
                                      title="Click to view full image"
                                    >
                                      <img src={att.url} alt={att.filename} className="teams-attachment-img" />
                                    </div>
                                  ) : (
                                    <a
                                      key={aIdx}
                                      href={att.url}
                                      download={att.filename}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="teams-attachment-card"
                                    >
                                      <div className="teams-attachment-card-icon">
                                        <FileText size={18} />
                                      </div>
                                      <div className="teams-attachment-card-info">
                                        <span className="teams-attachment-card-name">{att.filename}</span>
                                        <span className="teams-attachment-card-size">
                                          {(att.file_size / 1024).toFixed(1)} KB • Download
                                        </span>
                                      </div>
                                      <Download size={15} style={{ marginLeft: 'auto', color: '#64748b' }} />
                                    </a>
                                  )
                                )}
                              </div>
                            )}
                          </div>

                          {/* Reactions Pills */}
                          {msg.reactions && Object.keys(msg.reactions).length > 0 && (
                            <div className="teams-msg-reactions">
                              {Object.entries(msg.reactions).map(([emoji, usersList]) => {
                                const hasReacted = usersList.includes(myPrimaryId);
                                return (
                                  <button
                                    key={emoji}
                                    type="button"
                                    className={`teams-reaction-pill ${hasReacted ? 'reacted' : ''}`}
                                    onClick={() => handleToggleReaction(msg.id, emoji)}
                                    title={`Reacted by: ${usersList.join(', ')}`}
                                  >
                                    <span>{emoji}</span>
                                    <span>{usersList.length}</span>
                                  </button>
                                );
                              })}
                            </div>
                          )}

                          {/* Delivery status */}
                          {isMine && (
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '3px',
                                marginTop: '2px',
                                color: '#94a3b8',
                                fontSize: '0.7rem',
                              }}
                            >
                              <CheckCheck size={13} color="#0d9488" />
                              <span>Delivered</span>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {/* Hover Reaction & Actions Menu */}
                    {msg.sender_role !== 'system' && (
                      <div className="teams-msg-actions-hover">
                        {EMOJIS.slice(0, 4).map((em) => (
                          <button
                            key={em}
                            type="button"
                            className="teams-action-icon-btn"
                            onClick={() => handleToggleReaction(msg.id, em)}
                            title={`React with ${em}`}
                          >
                            {em}
                          </button>
                        ))}

                        <button
                          type="button"
                          className="teams-action-icon-btn"
                          onClick={() => {
                            setReplyingTo(msg);
                            setEditingMessage(null);
                            if (textareaRef.current) textareaRef.current.focus();
                          }}
                          title="Reply to message"
                        >
                          <Reply size={13} />
                        </button>

                        {(isMine || isAdmin) && (
                          <button
                            type="button"
                            className="teams-action-icon-btn"
                            onClick={() => handleStartEdit(msg)}
                            title="Edit message"
                          >
                            <Edit2 size={13} />
                          </button>
                        )}

                        <button
                          type="button"
                          className="teams-action-icon-btn"
                          onClick={() => handleTogglePin(msg.id)}
                          title={msg.is_pinned ? 'Unpin' : 'Pin message'}
                        >
                          <Pin size={13} />
                        </button>

                        {(isMine || isAdmin) && (
                          <button
                            type="button"
                            className="teams-action-icon-btn"
                            onClick={() => handleDeleteMessage(msg.id)}
                            title="Delete message"
                            style={{ color: '#ef4444' }}
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Typing Indicator Bar */}
          {typingNames.length > 0 && (
            <div className="teams-typing-bar">
              <div className="teams-typing-dots">
                <span className="teams-typing-dot" />
                <span className="teams-typing-dot" />
                <span className="teams-typing-dot" />
              </div>
              <span>
                {typingNames.join(', ')} {typingNames.length > 1 ? 'are' : 'is'} typing...
              </span>
            </div>
          )}

          {/* Input & Formatter Area */}
          <div className="teams-input-container">
            {/* Quick Replies Row */}
            <div className="teams-quick-replies">
              {QUICK_REPLIES.map((qr, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="teams-quick-chip"
                  onClick={() => setInputMessage(qr)}
                >
                  {qr}
                </button>
              ))}
            </div>

            {/* Quoting Preview if User Clicked Reply */}
            {replyingTo && (
              <div className="teams-replying-bar">
                <div>
                  <strong>Replying to {replyingTo.sender_name}:</strong>{' '}
                  <span style={{ opacity: 0.85 }}>{replyingTo.content.substring(0, 60)}...</span>
                </div>
                <button
                  type="button"
                  onClick={() => setReplyingTo(null)}
                  style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {/* Editing Message Banner */}
            {editingMessage && (
              <div className="teams-editing-bar">
                <div>
                  <strong>Editing message</strong> • Press Esc to cancel
                </div>
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {/* Attached file preview chip in composer */}
            {attachedFile && (
              <div className="teams-composer-attachment-preview">
                {attachedFile.is_image ? <ImageIcon size={16} /> : <FileText size={16} />}
                <span style={{ fontWeight: 600 }}>{attachedFile.filename}</span>
                <span style={{ fontSize: '0.75rem', opacity: 0.75 }}>
                  ({(attachedFile.file_size / 1024).toFixed(1)} KB)
                </span>
                <button
                  type="button"
                  onClick={() => setAttachedFile(null)}
                  style={{
                    marginLeft: 'auto',
                    background: 'transparent',
                    border: 'none',
                    color: '#dc2626',
                    cursor: 'pointer',
                  }}
                  title="Remove attachment"
                >
                  <X size={15} />
                </button>
              </div>
            )}

            <form onSubmit={handleSendMessage} className="teams-input-box">
              <textarea
                ref={textareaRef}
                rows={2}
                className="teams-textarea"
                placeholder={
                  editingMessage
                    ? 'Edit your message...'
                    : `Type a message to ${activeConversation.title}... (Shift+Enter for newline)`
                }
                value={inputMessage}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
              />

              <div className="teams-input-toolbar">
                <div className="teams-toolbar-left">
                  <button
                    type="button"
                    className="teams-tool-btn"
                    onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                    title="Insert Emoji"
                  >
                    <Smile size={18} />
                  </button>

                  <button
                    type="button"
                    className="teams-tool-btn"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    title="Attach file (Images, PDF, Word, Excel)"
                  >
                    {isUploading ? <Loader2 size={18} className="animate-spin" /> : <Paperclip size={18} />}
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={(!inputMessage.trim() && !attachedFile) || isSending}
                  className="teams-send-btn"
                >
                  {isSending ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : editingMessage ? (
                    <span>Save</span>
                  ) : (
                    <>
                      <Send size={15} />
                      <span>Send</span>
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Quick Floating Emoji Picker */}
            {showEmojiPicker && (
              <div
                style={{
                  position: 'absolute',
                  bottom: '90px',
                  left: '24px',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '12px',
                  padding: '8px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                  display: 'flex',
                  gap: '8px',
                  zIndex: 20,
                }}
              >
                {EMOJIS.map((em) => (
                  <button
                    key={em}
                    type="button"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      fontSize: '1.25rem',
                      cursor: 'pointer',
                      padding: '4px',
                    }}
                    onClick={() => {
                      setInputMessage((prev) => prev + em);
                      setShowEmojiPicker(false);
                    }}
                  >
                    {em}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
          Select or start a conversation
        </div>
      )}

      {/* 4. Right Side Details Drawer */}
      {isDetailsOpen && activeConversation && (
        <div className="teams-details-drawer">
          <div className="teams-drawer-header">
            <h4 className="teams-drawer-title">Details</h4>
            <button
              type="button"
              onClick={() => setIsDetailsOpen(false)}
              style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
            >
              <X size={18} />
            </button>
          </div>

          <div className="teams-profile-card">
            <div className="teams-profile-avatar-big">
              {activeConversation.type === 'team' ? <Hash size={34} /> : activeConversation.avatar || 'U'}
            </div>
            <div className="teams-profile-name">{activeConversation.title}</div>
            <div className="teams-profile-role">{activeConversation.subtitle}</div>
          </div>

          {activeConversation.type === 'team' ? (
            <div className="teams-details-section">
              {/* Leader meta */}
              <div className="teams-details-section-title">Team Leader</div>
              <div className="teams-member-item" style={{ marginBottom: '14px' }}>
                <div className="teams-member-avatar-mini">👑</div>
                <span style={{ fontWeight: 600 }}>{currentTeamObj?.leader || activeConversation.leader || 'Administrator'}</span>
              </div>

              {/* Group Members List */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div className="teams-details-section-title" style={{ margin: 0 }}>
                  Participants ({currentTeamObj?.members?.length || 0})
                </div>
                {(isAdmin || currentTeamObj?.created_by === myPrimaryId) && (
                  <button
                    type="button"
                    onClick={() => setShowAddMemberSelect(!showAddMemberSelect)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#0d9488',
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <UserPlus size={14} />
                    <span>Add</span>
                  </button>
                )}
              </div>

              {/* Add Member Dropdown inline */}
              {showAddMemberSelect && (
                <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '8px', marginBottom: '12px', border: '1px solid #e2e8f0' }}>
                  <select
                    value={selectedAddMemberId}
                    onChange={(e) => setSelectedAddMemberId(e.target.value)}
                    style={{ width: '100%', padding: '6px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.82rem', marginBottom: '8px' }}
                  >
                    <option value="">Select Employee to add...</option>
                    {contacts.map((c) => (
                      <option key={c.id} value={c.employee_id || c.id}>
                        {c.name} ({c.department})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleAddMemberToCurrentGroup}
                    disabled={!selectedAddMemberId}
                    style={{
                      width: '100%',
                      padding: '8px',
                      background: 'linear-gradient(135deg, #0b3d2b 0%, #0d9488 100%)',
                      color: '#ffffff',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: 700,
                      fontSize: '0.78rem',
                      cursor: 'pointer',
                    }}
                  >
                    Confirm Add to Group
                  </button>
                </div>
              )}

              {/* Members List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto', marginBottom: '16px' }}>
                {(currentTeamObj?.members || []).map((mId, idx) => {
                  const mContact = contacts.find(
                    (ct) => ct.id === mId || ct.employee_id === mId || ct.email === mId
                  );
                  const dispName = mContact ? mContact.name : mId;
                  const isSelf = String(mId).toLowerCase() === myPrimaryId.toLowerCase();

                  return (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 8px',
                        borderRadius: '6px',
                        backgroundColor: '#f8fafc',
                        fontSize: '0.82rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div
                          style={{
                            width: '24px',
                            height: '24px',
                            borderRadius: '50%',
                            backgroundColor: '#ccfbf1',
                            color: '#0f766e',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                          }}
                        >
                          {dispName[0].toUpperCase()}
                        </div>
                        <span>
                          {dispName} {isSelf ? '(You)' : ''}
                        </span>
                      </div>

                      {/* Remove button if admin or leave button if self */}
                      {(isAdmin || isSelf) && (
                        <button
                          type="button"
                          onClick={() => handleRemoveMemberFromGroup(mId)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: isSelf ? '#f59e0b' : '#ef4444',
                            cursor: 'pointer',
                            fontSize: '0.7rem',
                            fontWeight: 600,
                          }}
                          title={isSelf ? 'Leave group' : 'Remove from group'}
                        >
                          {isSelf ? 'Leave' : 'Remove'}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Shared Files in Team */}
              <div className="teams-details-section-title">Shared Attachments ({sharedAttachments.length})</div>
              {sharedAttachments.length === 0 ? (
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic', marginBottom: '16px' }}>
                  No shared files yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '160px', overflowY: 'auto', marginBottom: '16px' }}>
                  {sharedAttachments.map((att, aIdx) => (
                    <a
                      key={aIdx}
                      href={att.url}
                      download={att.filename}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '6px 8px',
                        borderRadius: '6px',
                        backgroundColor: '#f1f5f9',
                        textDecoration: 'none',
                        color: '#1e293b',
                        fontSize: '0.78rem',
                      }}
                    >
                      <FileText size={14} color="#0d9488" />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                        {att.filename}
                      </span>
                      <Download size={13} color="#64748b" />
                    </a>
                  ))}
                </div>
              )}

              {/* Channel Actions */}
              <div className="teams-details-section-title">Channel Actions</div>
              <button
                type="button"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid #a7f3d0',
                  backgroundColor: '#f0fdf4',
                  color: '#065f46',
                  fontSize: '0.82rem',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
                onClick={() => alert('Channel meeting scheduled.')}
              >
                <Calendar size={15} />
                <span>Schedule Team Meeting</span>
              </button>
            </div>
          ) : (
            <div className="teams-details-section">
              {/* Direct Chat Details */}
              <div className="teams-details-section-title">Shared Attachments ({sharedAttachments.length})</div>
              {sharedAttachments.length === 0 ? (
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic', marginBottom: '16px' }}>
                  No files shared yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '160px', overflowY: 'auto', marginBottom: '16px' }}>
                  {sharedAttachments.map((att, aIdx) => (
                    <a
                      key={aIdx}
                      href={att.url}
                      download={att.filename}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '6px 8px',
                        borderRadius: '6px',
                        backgroundColor: '#f1f5f9',
                        textDecoration: 'none',
                        color: '#1e293b',
                        fontSize: '0.78rem',
                      }}
                    >
                      <FileText size={14} color="#0d9488" />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                        {att.filename}
                      </span>
                      <Download size={13} color="#64748b" />
                    </a>
                  ))}
                </div>
              )}

              <div className="teams-details-section-title">Quick Actions</div>
              <button
                type="button"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid #a7f3d0',
                  backgroundColor: '#f0fdf4',
                  color: '#065f46',
                  fontSize: '0.82rem',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  marginBottom: '8px',
                }}
                onClick={() => alert(`Starting video call with ${activeConversation.title}...`)}
              >
                <Video size={15} />
                <span>Call on Teams</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* 5. "New Chat" & "New Group" Modal */}
      {isNewChatOpen && (
        <div className="teams-modal-backdrop" onClick={() => setIsNewChatOpen(false)}>
          <div className="teams-modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="teams-modal-header">
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#0f172a' }}>
                New Message or Group
              </h3>
              <button
                type="button"
                onClick={() => setIsNewChatOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Tabs: Direct Chat vs Create Team Channel */}
            <div className="teams-modal-tabs">
              <button
                type="button"
                className={`teams-modal-tab-btn ${modalTab === 'direct' ? 'active' : ''}`}
                onClick={() => setModalTab('direct')}
              >
                Direct Message
              </button>
              <button
                type="button"
                className={`teams-modal-tab-btn ${modalTab === 'group' ? 'active' : ''}`}
                onClick={() => setModalTab('group')}
              >
                Create Team Group
              </button>
            </div>

            <div className="teams-modal-body" style={{ maxHeight: '420px', overflowY: 'auto' }}>
              {modalTab === 'direct' ? (
                <>
                  {/* Team Channels Section */}
                  <div
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: '#64748b',
                      textTransform: 'uppercase',
                      marginBottom: '8px',
                    }}
                  >
                    Existing Team Channels
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '18px' }}>
                    {teams.map((t) => (
                      <div key={t.id} className="teams-modal-item" onClick={() => handleSelectTeamChannel(t)}>
                        <div
                          className="teams-avatar team"
                          style={{ width: '32px', height: '32px', borderRadius: '8px' }}
                        >
                          <Hash size={16} />
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>{t.name}</div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {t.department} &bull; {t.member_count} members
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Individual Contacts Section */}
                  <div
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: '#64748b',
                      textTransform: 'uppercase',
                      marginBottom: '8px',
                    }}
                  >
                    Direct Message (Employees & Admins)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {contacts.map((c) => (
                      <div key={c.id} className="teams-modal-item" onClick={() => handleStartChatWithContact(c)}>
                        <div className="teams-avatar-wrap" style={{ width: '32px', height: '32px' }}>
                          <div
                            className={`teams-avatar ${c.role}`}
                            style={{ width: '32px', height: '32px', borderRadius: '8px', fontSize: '0.85rem' }}
                          >
                            {c.avatar || 'U'}
                          </div>
                          <div className={`teams-presence-dot ${c.is_online ? 'online' : 'offline'}`} />
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>
                            {c.name} {c.role === 'admin' ? '(Admin)' : ''}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {c.designation} &bull; {c.department}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                /* Group Creation Form */
                <form onSubmit={handleCreateGroup} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Group Name *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g., Engineering Team, Project Titan"
                      value={newGroupName}
                      onChange={(e) => setNewGroupName(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid #cbd5e1',
                        fontSize: '0.88rem',
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Description (Optional)
                    </label>
                    <input
                      type="text"
                      placeholder="Purpose of this group conversation..."
                      value={newGroupDescription}
                      onChange={(e) => setNewGroupDescription(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid #cbd5e1',
                        fontSize: '0.88rem',
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                      Add Members ({selectedGroupMembers.length} selected)
                    </label>
                    <input
                      type="text"
                      placeholder="Search employees..."
                      value={groupMemberSearch}
                      onChange={(e) => setGroupMemberSearch(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        border: '1px solid #e2e8f0',
                        fontSize: '0.8rem',
                        marginBottom: '8px',
                      }}
                    />

                    <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '6px' }}>
                      {contacts
                        .filter(
                          (c) =>
                            !groupMemberSearch ||
                            c.name.toLowerCase().includes(groupMemberSearch.toLowerCase()) ||
                            c.department.toLowerCase().includes(groupMemberSearch.toLowerCase())
                        )
                        .map((c) => {
                          const isSelected = selectedGroupMembers.includes(c.employee_id || c.id);
                          return (
                            <div
                              key={c.id}
                              onClick={() => handleToggleMemberSelection(c.employee_id || c.id)}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                padding: '6px 8px',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                backgroundColor: isSelected ? '#f0fdf4' : 'transparent',
                              }}
                            >
                              <div
                                style={{
                                  width: '18px',
                                  height: '18px',
                                  borderRadius: '4px',
                                  border: isSelected ? '1px solid #0d9488' : '1px solid #cbd5e1',
                                  backgroundColor: isSelected ? '#0d9488' : '#ffffff',
                                  color: '#ffffff',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                }}
                              >
                                {isSelected && <Check size={12} />}
                              </div>
                              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#1e293b' }}>{c.name}</span>
                              <span style={{ fontSize: '0.72rem', color: '#64748b', marginLeft: 'auto' }}>
                                {c.department}
                              </span>
                            </div>
                          );
                        })}
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={!newGroupName.trim() || isCreatingGroup}
                    style={{
                      width: '100%',
                      padding: '10px',
                      background: 'linear-gradient(135deg, #0b3d2b 0%, #0d9488 100%)',
                      color: '#ffffff',
                      borderRadius: '8px',
                      border: 'none',
                      fontWeight: 700,
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                    }}
                  >
                    {isCreatingGroup ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                    <span>Create Group Channel</span>
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 6. Fullscreen Image Lightbox Modal */}
      {lightboxImage && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '24px',
          }}
          onClick={() => setLightboxImage(null)}
        >
          <button
            type="button"
            onClick={() => setLightboxImage(null)}
            style={{
              position: 'absolute',
              top: '20px',
              right: '20px',
              background: 'transparent',
              border: 'none',
              color: '#ffffff',
              cursor: 'pointer',
            }}
          >
            <X size={28} />
          </button>
          <img
            src={lightboxImage}
            alt="Preview"
            style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: '8px', objectFit: 'contain' }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
