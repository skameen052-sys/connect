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
  Info,
  Phone,
  Video,
  CheckCheck,
  X,
  Hash,
  Calendar,
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

  // UI states
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'direct', 'teams'
  const [searchQuery, setSearchQuery] = useState('');
  const [inputMessage, setInputMessage] = useState('');
  const [replyingTo, setReplyingTo] = useState(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isNewChatOpen, setIsNewChatOpen] = useState(false);
  const [typingUsers, setTypingUsers] = useState({});

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
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
          // Find contact to create ad-hoc active conversation
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
          const isCurrentTeam = activeConversation.type === 'team' && msg.chat_type === 'team' && (msg.team_id === activeConversation.target_id || msg.target_id === activeConversation.target_id);
          const isCurrentDirect = activeConversation.type === 'direct' && msg.chat_type === 'direct' && (
            msg.sender_id.toLowerCase() === activeConversation.target_id.toLowerCase() ||
            msg.receiver_id.toLowerCase() === activeConversation.target_id.toLowerCase()
          );

          if (isCurrentTeam || isCurrentDirect) {
            setMessages((prev) => {
              // Avoid duplicates
              if (prev.some((m) => m.id === msg.id)) return prev;
              return [...prev, msg];
            });
            setTimeout(() => scrollToBottom(true), 50);
          }
        }

        // Update conversation snippets
        setConversations((prev) =>
          prev.map((c) => {
            const matches = (c.type === 'team' && msg.chat_type === 'team' && c.target_id === (msg.team_id || msg.target_id)) ||
              (c.type === 'direct' && msg.chat_type === 'direct' && (c.target_id.toLowerCase() === msg.sender_id.toLowerCase() || c.target_id.toLowerCase() === msg.receiver_id.toLowerCase()));
            if (matches) {
              return {
                ...c,
                last_message: msg.content,
                last_message_sender: msg.sender_name,
                last_message_at: msg.created_at,
                unread_count: (activeConversation?.target_id === c.target_id) ? 0 : c.unread_count + 1,
              };
            }
            return c;
          })
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

    // Light polling interval (every 4 seconds) to ensure 100% synchronization
    const pollInterval = setInterval(() => {
      if (activeConversation) {
        chatService.getMessages(activeConversation.type, activeConversation.target_id)
          .then((fresh) => {
            if (Array.isArray(fresh)) {
              setMessages((prev) => {
                if (fresh.length !== prev.length || (fresh[fresh.length - 1]?.id !== prev[prev.length - 1]?.id)) {
                  setTimeout(() => scrollToBottom(true), 60);
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
  }, [activeConversation]);

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

  // Send message
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const cleanContent = inputMessage.trim();
    if (!cleanContent || !activeConversation || isSending) return;

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

      const created = await chatService.sendMessage({
        chatType: activeConversation.type,
        targetId: activeConversation.target_id,
        content: cleanContent,
        replyTo: replyData,
      });

      setMessages((prev) => [...prev, created]);
      setTimeout(() => scrollToBottom(true), 50);

      // Refresh conversations list to update snippet
      setConversations((prev) =>
        prev.map((c) =>
          c.conversation_id === activeConversation.conversation_id
            ? { ...c, last_message: cleanContent, last_message_at: new Date().toISOString() }
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

  // Keyboard shortcut: Enter to send, Shift+Enter for newline
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
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

  // Start new conversation from modal
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

  const handleSelectTeamChannel = (team) => {
    const existing = conversations.find(
      (c) => c.type === 'team' && c.target_id === String(team.id)
    );
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

  // Filter conversations
  const filteredConversations = conversations.filter((c) => {
    const matchesTab =
      activeTab === 'all' ||
      (activeTab === 'direct' && c.type === 'direct') ||
      (activeTab === 'teams' && c.type === 'team');
    const matchesQuery =
      !searchQuery ||
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.last_message && c.last_message.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesTab && matchesQuery;
  });

  const pinnedMessage = messages.find((m) => m.is_pinned);

  // Active typing list string
  const typingNames = Object.keys(typingUsers).filter((name) => typingUsers[name]);

  return (
    <div className="teams-chat-container animate-fade-in">
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
          onClick={() => setIsNewChatOpen(true)}
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
              onClick={() => setIsNewChatOpen(true)}
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

        {/* Filter Tabs: All, Direct, Teams */}
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
        </div>

        {/* Scrollable Conversation List */}
        <div className="teams-conversations-list">
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '32px 16px', color: '#64748b', fontSize: '0.85rem' }}>
              Loading conversations...
            </div>
          ) : filteredConversations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 16px', color: '#94a3b8', fontSize: '0.82rem' }}>
              No conversations found. Click <strong>New</strong> to start chatting!
            </div>
          ) : (
            filteredConversations.map((c) => {
              const isActive = activeConversation?.conversation_id === c.conversation_id;
              const hasUnread = (c.unread_count || 0) > 0;

              return (
                <button
                  key={c.conversation_id}
                  type="button"
                  className={`teams-conv-item ${isActive ? 'active' : ''} ${hasUnread ? 'unread' : ''}`}
                  onClick={() => setActiveConversation(c)}
                >
                  <div className="teams-avatar-wrap">
                    <div className={`teams-avatar ${c.type}`}>
                      {c.type === 'team' ? <Hash size={18} /> : (c.avatar || 'U')}
                    </div>
                    {c.type === 'direct' && (
                      <div className={`teams-presence-dot ${c.is_online ? 'online' : 'offline'}`} />
                    )}
                  </div>

                  <div className="teams-conv-meta">
                    <div className="teams-conv-header-line">
                      <span className="teams-conv-name">{c.title}</span>
                      {c.last_message_at && (
                        <span className="teams-conv-time">
                          {new Date(c.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                    <div className="teams-conv-preview-line">
                      <span className="teams-conv-snippet">
                        {c.last_message_sender ? `${c.last_message_sender}: ` : ''}
                        {c.last_message || c.subtitle}
                      </span>
                      {hasUnread && (
                        <span className="teams-conv-unread-pill">{c.unread_count}</span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* 3. Main Chat View Window */}
      {activeConversation ? (
        <div className="teams-main-chat">
          {/* Header Bar */}
          <div className="teams-chat-header">
            <div className="teams-header-left">
              <div className="teams-avatar-wrap">
                <div className={`teams-avatar ${activeConversation.type}`}>
                  {activeConversation.type === 'team' ? <Hash size={20} /> : (activeConversation.avatar || 'U')}
                </div>
                {activeConversation.type === 'direct' && (
                  <div className={`teams-presence-dot ${activeConversation.is_online ? 'online' : 'offline'}`} />
                )}
              </div>

              <div className="teams-header-details">
                <h3 className="teams-header-title">
                  <span>{activeConversation.title}</span>
                  {activeConversation.type === 'team' && (
                    <span className="teams-role-pill leader">TEAM CHANNEL</span>
                  )}
                </h3>
                <div className="teams-header-subtitle">
                  {activeConversation.type === 'direct' ? (
                    <span>{activeConversation.is_online ? 'Active now' : 'Offline'} &bull; {activeConversation.subtitle}</span>
                  ) : (
                    <span>{activeConversation.subtitle}</span>
                  )}
                </div>
              </div>
            </div>

            <div className="teams-header-actions">
              <button
                type="button"
                className="teams-header-action-btn"
                onClick={() => alert(`Starting voice/video call session with ${activeConversation.title}...`)}
                title="Start Teams Call"
              >
                <Phone size={16} />
              </button>
              <button
                type="button"
                className="teams-header-action-btn"
                onClick={() => alert(`Launching video conference room for ${activeConversation.title}...`)}
                title="Start Teams Video Meeting"
              >
                <Video size={16} />
              </button>
              <button
                type="button"
                className="teams-header-action-btn"
                onClick={() => setIsDetailsOpen(!isDetailsOpen)}
                title="View Team / Contact details"
              >
                <Info size={16} />
              </button>
            </div>
          </div>

          {/* Pinned Message Alert Strip */}
          {pinnedMessage && (
            <div className="teams-pinned-banner">
              <div className="teams-pinned-content">
                <Pin size={14} />
                <strong>Pinned:</strong>
                <span>{pinnedMessage.sender_name}: {pinnedMessage.content}</span>
              </div>
              <button
                type="button"
                style={{ background: 'transparent', border: 'none', color: '#1e40af', cursor: 'pointer', fontSize: '0.75rem', fontWeight: '700' }}
                onClick={() => handleTogglePin(pinnedMessage.id)}
              >
                Unpin
              </button>
            </div>
          )}

          {/* Messages Feed / Timeline */}
          <div className="teams-message-feed">
            <div className="teams-date-divider">
              <span>Today</span>
            </div>

            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94a3b8' }}>
                <MessageSquare size={36} style={{ margin: '0 auto 12px auto', opacity: 0.5 }} />
                <h4 style={{ margin: '0 0 6px 0', color: '#475569', fontSize: '1rem' }}>
                  No messages in this conversation yet
                </h4>
                <p style={{ margin: 0, fontSize: '0.85rem' }}>
                  Send a message below to kickstart the conversation with {activeConversation.title}.
                </p>
              </div>
            ) : (
              messages.map((msg) => {
                const isMine =
                  String(msg.sender_id).toLowerCase() === String(myPrimaryId).toLowerCase() ||
                  (isAdmin && msg.sender_role === 'admin');

                return (
                  <div
                    key={msg.id}
                    className={`teams-message-row ${isMine ? 'mine' : ''}`}
                  >
                    {!isMine && (
                      <div className="teams-msg-avatar">
                        {msg.sender_avatar || msg.sender_name?.[0] || 'U'}
                      </div>
                    )}

                    <div className="teams-msg-body">
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
                        {msg.is_pinned && <Pin size={12} color="#4f46e5" />}
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

                      {/* Read receipts */}
                      {isMine && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '3px', marginTop: '2px', color: '#94a3b8', fontSize: '0.7rem' }}>
                          <CheckCheck size={13} color="#4f46e5" />
                          <span>Delivered</span>
                        </div>
                      )}
                    </div>

                    {/* Hover Reaction & Actions Menu */}
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
                        onClick={() => setReplyingTo(msg)}
                        title="Reply to message"
                      >
                        <Reply size={13} />
                      </button>

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
              <span>{typingNames.join(', ')} {typingNames.length > 1 ? 'are' : 'is'} typing...</span>
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

            <form onSubmit={handleSendMessage} className="teams-input-box">
              <textarea
                ref={textareaRef}
                rows={2}
                className="teams-textarea"
                placeholder={`Type a message to ${activeConversation.title}... (Shift+Enter for newline)`}
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
                    onClick={() => alert('Attachment upload ready. Select file.')}
                    title="Attach file"
                  >
                    <Paperclip size={18} />
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isSending}
                  className="teams-send-btn"
                >
                  <Send size={15} />
                  <span>Send</span>
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
                    style={{ background: 'transparent', border: 'none', fontSize: '1.25rem', cursor: 'pointer', padding: '4px' }}
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
              {activeConversation.type === 'team' ? <Hash size={34} /> : (activeConversation.avatar || 'U')}
            </div>
            <div className="teams-profile-name">{activeConversation.title}</div>
            <div className="teams-profile-role">{activeConversation.subtitle}</div>
          </div>

          {activeConversation.type === 'team' ? (
            <div className="teams-details-section">
              <div className="teams-details-section-title">Team Leader</div>
              <div className="teams-member-item">
                <div className="teams-member-avatar-mini">👑</div>
                <span>{activeConversation.leader || 'Administrator'}</span>
              </div>

              <div className="teams-details-section-title" style={{ marginTop: '16px' }}>
                Channel Actions
              </div>
              <button
                type="button"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid #c7d2fe',
                  backgroundColor: '#eef2ff',
                  color: '#4f46e5',
                  fontSize: '0.82rem',
                  fontWeight: '600',
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
              <div className="teams-details-section-title">Direct Actions</div>
              <button
                type="button"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: '1px solid #c7d2fe',
                  backgroundColor: '#eef2ff',
                  color: '#4f46e5',
                  fontSize: '0.82rem',
                  fontWeight: '600',
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

      {/* 5. "New Chat" Modal (Allows selecting any employee or team) */}
      {isNewChatOpen && (
        <div className="teams-modal-backdrop" onClick={() => setIsNewChatOpen(false)}>
          <div className="teams-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="teams-modal-header">
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#0f172a' }}>
                Start a New Chat
              </h3>
              <button
                type="button"
                onClick={() => setIsNewChatOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="teams-modal-body">
              {/* Teams Channels Section */}
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: '8px' }}>
                Team Channels
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '18px' }}>
                {teams.map((t) => (
                  <div
                    key={t.id}
                    className="teams-modal-item"
                    onClick={() => handleSelectTeamChannel(t)}
                  >
                    <div className="teams-avatar team" style={{ width: '32px', height: '32px', borderRadius: '8px' }}>
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
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: '8px' }}>
                Direct Message (Individual Employee / Admin)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {contacts.map((c) => (
                  <div
                    key={c.id}
                    className="teams-modal-item"
                    onClick={() => handleStartChatWithContact(c)}
                  >
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
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
