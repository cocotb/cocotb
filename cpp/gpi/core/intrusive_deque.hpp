#ifndef INTRUSIVE_DEQUE_HPP
#define INTRUSIVE_DEQUE_HPP

// This is a special deque implementation seen in the EventLoop, Futures,
// TaskManagers, and more. This deque does not own the nodes it contains (beyond
// the default-constructed anchor), so it is unconcerned with object lifetimes.
// Nodes are inserted into the deque and by nature of their structure, can be
// removed anonymously in O(1). Node is a base class for all types that wish to
// be added to an IntrusiveDeque.

#include <iterator>
#include <type_traits>
#include <utility>

namespace detail {

template <typename EntryT>
class IntrusiveDeque;

class IntrusiveDequeNode {
    template <typename>
    friend class IntrusiveDeque;

  protected:
    void deque_remove() noexcept {
        if (prev == this) {
            return;
        }
        prev->next = next;
        next->prev = prev;
        prev = this;
        next = this;
    }

  private:
    // Self-linked when not in a deque; the anchor of an empty deque uses the
    // same convention (see IntrusiveDeque::clear).
    IntrusiveDequeNode *prev = this;
    IntrusiveDequeNode *next = this;
};

template <typename EntryT>
class IntrusiveDeque {
    static_assert(std::is_base_of<IntrusiveDequeNode, EntryT>::value,
                  "EntryT must derive from IntrusiveDequeNode");

  public:
    IntrusiveDeque() noexcept = default;
    // Non-owning entries must be unique, so copying is banned.
    IntrusiveDeque(IntrusiveDeque const &) = delete;
    IntrusiveDeque &operator=(IntrusiveDeque const &) = delete;

    IntrusiveDeque(IntrusiveDeque &&other) noexcept {
        extend_back(std::move(other));
    }
    IntrusiveDeque &operator=(IntrusiveDeque &&other) noexcept {
        if (this != &other) {
            clear();
            extend_back(std::move(other));
        }
        return *this;
    }

  public:
    template <typename NodeType, bool Forward>
    class Iterator {
        friend class IntrusiveDeque;

        using RawNode =
            typename std::conditional<std::is_const<NodeType>::value,
                                      IntrusiveDequeNode const,
                                      IntrusiveDequeNode>::type;
        RawNode *current;

        explicit Iterator(RawNode *node) noexcept : current(node) {}

      public:
        using iterator_category = std::bidirectional_iterator_tag;
        using value_type = typename std::remove_const<NodeType>::type;
        using difference_type = std::ptrdiff_t;
        using pointer = NodeType *;
        using reference = NodeType &;

        Iterator() noexcept : current(nullptr) {}

        reference operator*() const noexcept {
            return *static_cast<pointer>(current);
        }
        pointer operator->() const noexcept {
            return static_cast<pointer>(current);
        }

        Iterator &operator++() noexcept {
            current = Forward ? current->next : current->prev;
            return *this;
        }
        Iterator operator++(int) noexcept {
            Iterator tmp = *this;
            ++*this;
            return tmp;
        }
        Iterator &operator--() noexcept {
            current = Forward ? current->prev : current->next;
            return *this;
        }
        Iterator operator--(int) noexcept {
            Iterator tmp = *this;
            --*this;
            return tmp;
        }

        bool operator==(Iterator const &other) const noexcept {
            return current == other.current;
        }
        bool operator!=(Iterator const &other) const noexcept {
            return current != other.current;
        }
    };

    using iterator = Iterator<EntryT, true>;
    using const_iterator = Iterator<EntryT const, true>;
    using reverse_iterator = Iterator<EntryT, false>;
    using const_reverse_iterator = Iterator<EntryT const, false>;

    iterator begin() noexcept { return iterator(anchor.next); }
    iterator end() noexcept { return iterator(&anchor); }
    const_iterator begin() const noexcept {
        return const_iterator(anchor.next);
    }
    const_iterator end() const noexcept { return const_iterator(&anchor); }
    reverse_iterator rbegin() noexcept { return reverse_iterator(anchor.prev); }
    reverse_iterator rend() noexcept { return reverse_iterator(&anchor); }
    const_reverse_iterator rbegin() const noexcept {
        return const_reverse_iterator(anchor.prev);
    }
    const_reverse_iterator rend() const noexcept {
        return const_reverse_iterator(&anchor);
    }

  public:
    EntryT *front() const noexcept {
        return empty() ? nullptr : static_cast<EntryT *>(anchor.next);
    }
    EntryT *back() const noexcept {
        return empty() ? nullptr : static_cast<EntryT *>(anchor.prev);
    }
    bool empty() const noexcept { return anchor.next == &anchor; }
    EntryT *push_back(EntryT *node) noexcept {
        node->prev = anchor.prev;
        node->next = &anchor;
        anchor.prev->next = node;
        anchor.prev = node;
        return node;
    }
    EntryT *push_front(EntryT *node) noexcept {
        node->prev = &anchor;
        node->next = anchor.next;
        anchor.next->prev = node;
        anchor.next = node;
        return node;
    }
    EntryT *pop_back() noexcept {
        if (empty()) {
            return nullptr;
        }
        IntrusiveDequeNode *node = anchor.prev;
        node->deque_remove();
        return static_cast<EntryT *>(node);
    }
    EntryT *pop_front() noexcept {
        if (empty()) {
            return nullptr;
        }
        IntrusiveDequeNode *node = anchor.next;
        node->deque_remove();
        return static_cast<EntryT *>(node);
    }
    void extend_back(IntrusiveDeque<EntryT> &&other) noexcept {
        if (other.empty()) {
            return;
        }
        IntrusiveDequeNode *first = other.anchor.next;
        IntrusiveDequeNode *last = other.anchor.prev;
        first->prev = anchor.prev;
        last->next = &anchor;
        anchor.prev->next = first;
        anchor.prev = last;
        other.clear();
    }
    void extend_front(IntrusiveDeque<EntryT> &&other) noexcept {
        if (other.empty()) {
            return;
        }
        IntrusiveDequeNode *first = other.anchor.next;
        IntrusiveDequeNode *last = other.anchor.prev;
        first->prev = &anchor;
        last->next = anchor.next;
        anchor.next->prev = last;
        anchor.next = first;
        other.clear();
    }
    void clear() noexcept {
        anchor.next = &anchor;
        anchor.prev = &anchor;
    }

  private:
    IntrusiveDequeNode anchor;
};

}  // namespace detail

#endif  // INTRUSIVE_DEQUE_HPP
