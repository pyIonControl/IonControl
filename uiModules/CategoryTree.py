# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from PyQt5 import QtCore, QtGui, QtWidgets
from modules.enum import enum
from modules.Utility import indexWithDefault
from sys import getrefcount
from uiModules.KeyboardFilter import KeyListFilter
from copy import copy

nodeTypes = enum('category', 'data')

class Node(object):
    """Class for tree nodes"""
    def __init__(self, parent, id, nodeType, content):
        self.parent = parent #parent node
        self.id = id #All nodes need a unique id
        self.content = content #content is the actual data in the tree, it can be anything
        self.children = []
        self.nodeType = nodeType #nodeTypes.category or nodeTypes.data
        self.isBold = False #Determines whether node is shown bold
        self.bgColor = None #background color

    def childCount(self):
        return len(self.children)

    def child(self, row):
        if 0 <= row < self.childCount():
            return self.children[row]

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id==other.id

    def __str__(self):
        return "Node: " + str(self.id)

    @property
    def row(self):
        """Return this node's row in its parent's list of children"""
        return self.parent.children.index(self) if (self.parent and self.parent.children) else 0

    @row.setter
    def row(self, newRow):
        if 0 <= newRow < len(self.parent.children):
            self.parent.children.insert( newRow, self.parent.children.pop(self.row) )

    def __hash__(self):
        return hash(self.id)


class CategoryTreeModel(QtCore.QAbstractItemModel):
    """Base class for category trees.

    A category tree is a simplified tree structure in which a flat list of data is broken down by categories. It
    is intended to be an extension of a table model, in which the elements of the table are broken down into different
    categories. The data itself is not hierarchical. For that reasons, the data can be presented to the model as a
    flat list. If a given element of the list has an attribute defined by categoriesAttr, then that element will be displayed
    beneath those categories. categoriesAttr is a list of strings, with the most general category first. If categoriesAttr
    is a string, it is interpreted as a list of strings of length 1.

    Other attributes that are respected are "hasDepedency" and "isBold." If the content has one of those attributes,
    the content is displayed accordingly.
    """
    def __init__(self, contentList=[], parent=None, categoriesAttr='categories', nodeNameAttr='name'):
        super(CategoryTreeModel, self).__init__(parent)
        #attribute that determines how to categorize content
        self.categoriesAttr = categoriesAttr
        #attribute that determines node names
        self.nodeNameAttr = nodeNameAttr

        #styling for different types of content
        self.dependencyBgColor = QtGui.QColor(QtCore.Qt.green).lighter(175)
        self.defaultFontName = "Segoe UI"
        self.defaultFontSize = 9
        self.normalFont = QtGui.QFont(self.defaultFontName, self.defaultFontSize, QtGui.QFont.Normal)
        self.boldFont = QtGui.QFont(self.defaultFontName, self.defaultFontSize, QtGui.QFont.Bold)

        #lookups to determine the appearance of the model
        self.fontLookup = {True:self.boldFont, False:self.normalFont}
        self.headerLookup = {} #overwrite to set headers. key: (orientation, role, section) val: str
        self.dataLookup = {
                           (QtCore.Qt.DisplayRole, 0):
                               lambda node: str(node.content) #default, normally overwritten
                           }
        self.dependencyBgFunction = lambda node: self.dependencyBgColor if getattr(node.content, 'hasDependency', None) else getattr(node, 'bgColor', None)
        self.toolTipFunction = lambda node: getattr(node.content, 'string', '') if getattr(node.content, 'hasDependency', None) else None
        self.dataAllColLookup = {   #data lookup that applies to all columns
            QtCore.Qt.FontRole: lambda node: self.fontLookup.get(getattr(node, 'isBold', False)),
            QtCore.Qt.BackgroundRole: lambda node: getattr(node, 'bgColor', None)
            }
        self.categoryDataLookup = {(QtCore.Qt.DisplayRole, 0): lambda node: node.content}
        self.categoryDataAllColLookup = {
            QtCore.Qt.FontRole: lambda node: self.fontLookup.get(getattr(node, 'isBold', False)),
            QtCore.Qt.BackgroundRole: lambda node: getattr(node, 'bgColor', None)
        }
        self.setDataLookup = {} #overwrite to set data. key: (role, col). val: function that takes (index, value)
        self.categorySetDataLookup = {} #overwrite to set data. key: (role, col). val: function that takes (index, value)
        self.flagsLookup = {0: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable} #default, normally overwritten
        self.categoryFlagsLookup = {0: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable}
        self.numColumns = 1 #Overwrite with number of columns
        self.allowReordering = False #If True, nodes can be moved around
        self.allowDeletion = False #If True, nodes can be deleted
        self.root = Node(parent=None, id='', nodeType=nodeTypes.category, content=None)
        self.nodeDict = {'': self.root} #dictionary of all nodes, with string indicating hierarchy to that item
        #contentList is a list of objects. Can be anything. If the objects have a category attribute, a tree will result.
        self.addNodeList(contentList)

    def nodeFromIndex(self, index):
        """Return the node at the given index"""
        return index.internalPointer() if index.isValid() else self.root

    def indexFromNode(self, node, col=0):
        """Return a model index for the given node column"""
        if node == self.root:
            return QtCore.QModelIndex()
        else:
            parentIndex = QtCore.QModelIndex() if node.parent==self.root else self.indexFromNode(node.parent) #recursive
            return self.index(node.row, col, parentIndex)

    def getLocation(self, index):
        """Return the node, column at the given index"""
        node = self.nodeFromIndex(index)
        return node, index.column()

    def index(self, row, column, parentIndex):
        """Return a model index for the node at the given row, column, parentIndex"""
        if not self.hasIndex(row, column, parentIndex):
            ind = QtCore.QModelIndex()
        else:
            parentNode = self.nodeFromIndex(parentIndex)
            node = parentNode.child(row)
            ind = self.createIndex(row, column, node) if node else QtCore.QModelIndex()
        return ind

    def rowCount(self, index):
        node = self.nodeFromIndex(index)
        return node.childCount()

    def columnCount(self, index):
        return self.numColumns

    def data(self, index, role):
        node, col = self.getLocation(index)
        if node.nodeType==nodeTypes.category:
            return self.categoryDataLookup.get( (role, col), self.categoryDataAllColLookup.get(role, lambda node: None))(node)
        else:
            return self.dataLookup.get( (role, col), self.dataAllColLookup.get(role, lambda node: None))(node)

    def setData(self, index, value, role):
        node, col = self.getLocation(index)
        if node.nodeType==nodeTypes.category:
            return self.categorySetDataLookup.get( (role, col), lambda index, value: False)(index, value)
        else:
            return self.setDataLookup.get( (role, col), lambda index, value: False)(index, value)

    def parent(self, index):
        node = self.nodeFromIndex(index)
        parentNode = node.parent
        return QtCore.QModelIndex() if (node == self.root or parentNode == self.root) else self.createIndex(parentNode.row, 0, parentNode)

    def flags(self, index ):
        node, col = self.getLocation(index)
        if node.nodeType==nodeTypes.category:
            return self.categoryFlagsLookup.get(col, QtCore.Qt.NoItemFlags)
        else:
            return self.flagsLookup.get(col, QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

    def headerData(self, section, orientation, role):
        return self.headerLookup.get((orientation, role, section))

    def addNodeList(self, contentList):
        """Add a list of nodes to the tree"""
        for listIndex, content in enumerate(contentList):
            name = getattr(content, self.nodeNameAttr, str(listIndex))
            self.addNode(content, name)

    def addNode(self, content, name=None):
        """Add a node to the tree containing 'content' with name 'name'. Return new Node."""
        if not name:
            name = getattr(content, self.nodeNameAttr, '')
        name = str(name)
        categories = getattr(content, self.categoriesAttr, None)
        if categories:
            if categories.__class__!=list:
                categories = [categories]  # make a list of one if it's not a list
            categories = list(map(str, categories)) #make sure it's a list of strings
            parent = self.makeCategoryNodes(categories)
        else:
            parent = self.root
        nodeID = parent.id+'_'+name if parent.id else name
        nodeType = nodeTypes.data
        if nodeID in self.nodeDict: #nodeIDs must be unique. If the nodeID has already been used, we add "_n" to the ID and increment 'n' until we find an available ID
            count=0
            baseNodeID = nodeID
            while nodeID in self.nodeDict:
                nodeID = baseNodeID+"_{0}".format(count)
                count+=1
        node = Node(parent, nodeID, nodeType, content)
        self.addRow(parent, node)
        self.nodeDict[nodeID] = node
        return node

    def removeNode(self, node, useModelReset=False):
        """Remove the specified node from the tree
        if useModelReset is True, the calling function will use beginModelReset and endModelReset."""
        if self.allowDeletion and node!=self.root:
            dataNodes = self.getDataNodes(node)
            okToDelete = [getattr(dataNode.content, 'okToDelete', True) for dataNode in dataNodes]
            if all(okToDelete):
                for childNode in node.children:
                    self.removeNode(childNode, useModelReset) #recursively delete children
                parent = node.parent
                row = node.row
                nodeID = node.id
                parentIndex = self.indexFromNode(parent)
                if not useModelReset:
                    self.beginRemoveRows(parentIndex, row, row)
                del parent.children[row]
                del self.nodeDict[nodeID]
                deletedID = copy(node.id)
                del node
                if not useModelReset:
                    self.endRemoveRows()
                return deletedID

    def makeCategoryNodes(self, categories):
        """Recursively creates tree nodes from the provided list of categories"""
        key = '_'.join(categories)
        if key not in self.nodeDict: #the empty key will always be in the dictionary, so the recursion will end
            parent = self.makeCategoryNodes(categories[:-1]) #This is the recursive step
            name = categories[-1]
            node = Node(parent=parent, id=parent.id+'_'+name if parent.id else name, nodeType=nodeTypes.category, content=name)
            self.addRow(parent, node)
            self.nodeDict[key] = node
        return self.nodeDict[key]

    def addRow(self, parent, node):
        """Add 'node' to the table under 'parent'"""
        parentIndex = self.indexFromNode(parent)
        self.beginInsertRows(parentIndex, parent.childCount(), parent.childCount())
        parent.children.append(node)
        self.endInsertRows()

    def nodeFromContent(self, content):
        """Get the node associated with the specified content.

        This is an inefficient O(n) search. However, there is no other way to do this reverse lookup without
        making assumptions about the nature of 'content'. Child classes can re-implement this function to
        make it more efficient."""
        success=False
        for node in self.nodeDict.values():
            if node.content==content:
                success=True
                break
        return node if success else None

    def nodeFromId(self, id):
        """return the node associated with the specified node id"""
        return self.nodeDict.get(id)

    def changeCategory(self, node, categories=None, deleteOldIfEmpty=True):
        """change node category
        Args:
            node (Node): the node to move
            categories (str or list[str]): new category(ies) for node. defaults to None
            deleteOldIfEmpty (bool): if True, delete the node's former category node if it is now empty
        """
        name = str(getattr(node.content, self.nodeNameAttr, ''))
        oldParent = node.parent
        oldID = copy(node.id)
        oldRow = copy(node.row)
        if categories:
            categories = [categories] if categories.__class__!=list else categories # make a list of one if it's not a list
            categories = list(map(str, categories)) #make sure it's a list of strings
            newParent = self.makeCategoryNodes(categories)
        else:
            newParent = self.root
        newID = newParent.id+'_'+name if newParent.id else name
        if newID in self.nodeDict: #nodeIDs must be unique. If the nodeID has already been used, we add "_n" to the ID and increment 'n' until we find an available ID
            count=0
            baseNodeID = newID
            while newID in self.nodeDict:
                newID = baseNodeID+"_{0}".format(count)
                count+=1
        #remove node from dict, oldParent children
        oldParentIndex = self.indexFromNode(oldParent)
        self.beginRemoveRows(oldParentIndex, oldRow, oldRow)
        del oldParent.children[oldRow]
        del self.nodeDict[oldID]
        self.endRemoveRows()
        #add node to new parent
        node.id = newID
        node.parent = newParent
        self.addRow(newParent, node)
        self.nodeDict[newID] = node
        #delete old category node if necessary
        oldDeleted, deletedCategoryNodeIDs = self.removeAllEmptyParents(oldParent) if deleteOldIfEmpty else False, []
        return node, oldDeleted, deletedCategoryNodeIDs

    def removeAllEmptyParents(self, oldParent):
        if oldParent.children==[] and oldParent != self.root:
            deletedID = self.removeNode(oldParent)
            allDeletedCategoryNodeIDs = [deletedID]
            oldDeleted, deletedCategoryNodeIDs = self.removeAllEmptyParents(oldParent.parent)
            if oldDeleted:
                allDeletedCategoryNodeIDs.extend(deletedCategoryNodeIDs)
            return True, allDeletedCategoryNodeIDs
        return False, []

    def clear(self):
        """clear the tree content"""
        self.root.children = []
        self.nodeDict = {'': self.root}

    def moveRow(self, index, up):
        """move modelIndex 'index' up if up is True, else down"""
        node=self.nodeFromIndex(index)
        delta = -1 if up else 1
        parentIndex=self.indexFromNode(node.parent)
        if 0 <= node.row+delta < len(node.parent.children):
            moveValid = self.beginMoveRows(parentIndex, node.row, node.row, parentIndex, node.row-1 if up else node.row+2)
            if moveValid:
                node.row += delta
                self.endMoveRows()

    def contentFromIndex(self, index):
        """Get the content associated with the given index"""
        return self.nodeFromIndex(index).content

    def getTopNode(self, node):
        """Return the highest level category node before root in the tree above node"""
        return None if node is self.root else (node if node.parent is self.root else self.getTopNode(node.parent)) #recursive

    def getFirstDataNode(self, node):
        """Return the first data node under (and including) node"""
        return node if node.nodeType==nodeTypes.data else (self.getFirstDataNode(node.children[0]) if node.children else None)

    def getLastDataNode(self, node):
        """Return the last data node under (and including) node"""
        return node if node.nodeType==nodeTypes.data else (self.getLastDataNode(node.children[-1]) if node.children else None)

    def getDataNodes(self, node):
        """Get a list of all data nodes under (and including) node"""
        dataNodes = []
        if node.nodeType==nodeTypes.data:
            dataNodes=[node]
        else:
            for childNode in node.children:
                childSubNodes = self.getDataNodes(childNode) #recursive step
                if childSubNodes:
                    dataNodes.extend(childSubNodes)
        return dataNodes


class CategoryTreeView(QtWidgets.QTreeView):
    """Class for viewing category trees"""
    def __init__(self, parent=None):
        super(CategoryTreeView, self).__init__(parent)
        self.filter = KeyListFilter( [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown, QtCore.Qt.Key_Delete],
                                     [QtCore.Qt.Key_B, QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_W, QtCore.Qt.Key_R] )
        self.filter.keyPressed.connect(self.onKey)
        self.filter.controlKeyPressed.connect(self.onControl)
        self.installEventFilter(self.filter)

    def onKey(self, key):
        if key==QtCore.Qt.Key_Delete:
            self.onDelete()
        elif key in [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown]:
            up = key==QtCore.Qt.Key_PageUp
            self.onReorder(up)

    def onControl(self, key):
        if key==QtCore.Qt.Key_B:
            self.onBold()
        elif key==QtCore.Qt.Key_Up:
            self.collapseAll()
        elif key==QtCore.Qt.Key_Down:
            self.expandAll()
        elif key==QtCore.Qt.Key_W:
            self.onSetBackgroundColor()
        elif key==QtCore.Qt.Key_R:
            self.onRemoveBackgroundColor()

    def onBold(self):
        indexList = self.selectedRowIndexes()
        model=self.model()
        for leftIndex in indexList:
            node=model.nodeFromIndex(leftIndex)
            node.isBold = not node.isBold if hasattr(node, 'isBold') else True
            rightIndex = model.indexFromNode(node, model.numColumns-1)
            model.dataChanged.emit(leftIndex, rightIndex)

    def onDelete(self):
        model=self.model()
        if model.allowDeletion:
            selectedNodes = self.selectedNodes()
            useModelReset = len(selectedNodes)>10
            topNodeList = [node for node in selectedNodes if node.parent not in selectedNodes]
            if useModelReset:
                model.beginResetModel()
            for node in topNodeList:
                if node!=model.root: #don't delete root
                    model.removeNode(node, useModelReset)
            if useModelReset:
                model.endResetModel()

    def onReorder(self, up):
        if self.model().allowReordering:
            indexList = self.selectedRowIndexes()
            if not up: indexList.reverse()
            for index in indexList:
                self.model().moveRow(index, up)

    def selectedRowIndexes(self, col=0):
        """Returns a list of unique model indexes corresponding to column 'col' of each selected element, sorted by row.

        Built-in selectionModel().selectedRows function seems to have a bug"""
        return [self.model().indexFromNode(node, col) for node in self.selectedNodes()]

    def selectedNodes(self):
        """Same as selectedRows, but returns list of nodes rather than list of model indexes"""
        allIndexList = self.selectedIndexes()
        nodes = set()
        for index in allIndexList:
            node = self.model().nodeFromIndex(index)
            nodes.add(node)
        nodeList = list(nodes)
        nodeList.sort(key=lambda node: node.row)
        return nodeList

    def selectedTopIndexes(self, col=0):
        """Returns list of unique top level model indexes corresponding to column 'col' of the top level of each selected element, sorted by row."""
        return [self.model().indexFromNode(node, col) for node in self.selectedTopNodes()]

    def selectedTopNodes(self):
        """Same as selectedTopIndexes, but returns list of nodes rather than list of model indexes"""
        nodeList = self.selectedNodes()
        topNodeList = []
        for node in nodeList:
            topNode=self.model().getTopNode(node)
            if topNode not in topNodeList:
                topNodeList.append(topNode)
        return topNodeList

    def selectedDataNodes(self):
        """Returns list of first data nodes of selected nodes"""
        nodeList = self.selectedNodes()
        dataNodeList = []
        for node in nodeList:
            firstDataNode=self.model().getFirstDataNode(node)
            if firstDataNode:
                dataNodeList.append(firstDataNode)
        return dataNodeList

    def treeState(self):
        """Returns tree state for saving config"""
        columnWidths = self.header().saveState()
        return self.treeColumnWidth(), self.treeMarkup()

    def treeColumnWidth(self):
        return self.header().saveState()

    @staticmethod
    def colorName(child):
        color = getattr(child, 'bgColor', None)
        return str(color.name()) if color else None

    def treeMarkup(self):
        nodeStates = {}
        for key, node in self.model().nodeDict.items():
            nodeStates[node.id] = [( child.id,
                                     getattr(child, 'isBold', False),
                                     self.isExpanded(self.model().indexFromNode(child)),
                                     self.colorName(child))
                                     for child in node.children]
        return nodeStates

    def restoreTreeState(self, state):
        """load in a tree state from the given column widths and state"""
        if state:
            columnWidths, nodeStates = state
            self.restoreTreeColumnWidth(columnWidths)
            self.restoreTreeMarkup(nodeStates)

    def restoreTreeColumnWidth(self, columnWidths):
        if columnWidths:
            self.header().restoreState(columnWidths)

    def restoreTreeMarkup(self, nodeStates):
        if nodeStates:
            if self.model().allowReordering:
                self.model().beginResetModel()
                for parentID, childDataList in nodeStates.items():
                    parentNode = self.model().nodeFromId(parentID)
                    if parentNode:
                        childIDList = [childData[0] for childData in childDataList]
                        parentNode.children.sort(key=lambda childNode: indexWithDefault(childIDList, childNode.id))
                self.model().endResetModel()
            for nodeDataList in nodeStates.values():
                for nodeData in nodeDataList:
                    nodeID, isBold, expanded, bgColor = nodeData
                    if nodeID in self.model().nodeDict:
                        node = self.model().nodeDict[nodeID]
                        node.isBold = isBold
                        node.bgColor = QtGui.QColor(bgColor) if bgColor else None
                        if expanded:
                            index = self.model().indexFromNode(node)
                            self.expand(index)

    def onSetBackgroundColor(self):
        color = QtWidgets.QColorDialog.getColor()
        if not color.isValid():
            color = None
        self.setBackgroundColor(color)

    def onRemoveBackgroundColor(self):
        self.setBackgroundColor(None)

    def setBackgroundColor(self, color):
        nodes = self.selectedNodes()
        model = self.model()
        for node in nodes:
            node.bgColor = color
            leftIndex = model.indexFromNode(node, 0)
            rightIndex = model.indexFromNode(node, model.numColumns-1)
            model.dataChanged.emit(leftIndex, rightIndex)

    def expandToNode(self, node):
        """Expand all parents above specified node"""
        model = self.model()
        parentNode = node.parent
        if parentNode != model.root:
            parentIndex = model.indexFromNode(parentNode)
            self.expand(parentIndex)
            self.expandToNode(parentNode)



if __name__ == "__main__":
    import sys
    from functools import partial
    app = QtWidgets.QApplication(sys.argv)
    class myContent(object):
        def __init__(self, data1, data2, categories=None, hasDependency=False, string='', isBold=False):
            self.data1 = data1
            self.data2 = data2
            self.categories = categories
            self.hasDependency = hasDependency
            self.string = string
            self.isBold = isBold
        def __str__(self):
            return str((str(self.data1), str(self.data2)))
    class myModel(CategoryTreeModel):
        def __init__(self, contentList=[], parent=None, categoriesAttr='categories', nodeNameAttr='name'):
            super(myModel, self).__init__(contentList, parent, categoriesAttr, nodeNameAttr)
            self.numColumns=2
            self.allowReordering=True
            self.allowDeletion=True
            self.headerLookup.update({
                    (QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole, 0): 'Name',
                    (QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole, 1): 'Value'
                    })
            self.dataLookup.update({
                           (QtCore.Qt.DisplayRole, 0):
                               lambda node: str(node.content.data1),
                           (QtCore.Qt.DisplayRole, 1):
                               lambda node: str(node.content.data2),
                           (QtCore.Qt.EditRole, 1):
                               lambda node: str(node.content.data2)
                           })
            self.setDataLookup.update({
                (QtCore.Qt.EditRole, 1): lambda index, value: self.setValue(index, value)
                })
            self.flagsLookup.update({
                0: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable,
                1: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
                })

        def setValue(self, index, value):
            node = self.nodeFromIndex(index)
            node.content.data2 = value
            return True

    model = myModel([myContent('hot dog', 3, ['Foods', 'Red'], True, 'qq', isBold=True),
                     myContent('grapes', 3, ['Foods'], True, 'qq', isBold=True),
                     myContent('strawberry', 4, ['Foods', 'Red']),
                     myContent('blueberry', 12, ['Foods', 'Blue'], isBold=True),
                     myContent('golf', 2, ['Games', 'ball based'], True, 'abc'),
                     myContent('baseball', 12, ['Games', 'ball based']),
                     myContent('hockey', 13, ['Games', 'puck based']),
                     myContent('People', 12, ['People']),
                     myContent('Huey', 225, ['People']),
                     myContent('Dewey', 1251, ['People']),
                     myContent('Louie', 12, ['People']),
                     myContent('other', 125121)
                     ], nodeNameAttr='data1')
    view = CategoryTreeView()
    view.setModel(model)
    view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
    window = QtWidgets.QMainWindow()
    dock = QtWidgets.QDockWidget("Category Tree View")
    dock.setWidget(view)
    window.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)
    button = QtWidgets.QPushButton('move')
    button.clicked.connect(partial(model.changeCategory, model.nodeDict['Games_ball based_golf'], ['a', 'b', 'c']))

    window.setCentralWidget(button)
    view.expandAll()
    view.resizeColumnToContents(0)
    view.resizeColumnToContents(1)
    window.show()
    sys.exit(app.exec_())