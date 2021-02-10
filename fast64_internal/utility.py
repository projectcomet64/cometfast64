import bpy
from math import pi, ceil, degrees, radians
from mathutils import *
from .sm64_constants import *
from .sm64_geolayout_constants import *
import random
import string
import os
import math
import traceback
import re
import os
from .utility_anim import *

class PluginError(Exception):
	pass

class VertexWeightError(PluginError):
	pass

def findStartBones(armatureObj):
	noParentBones = sorted([bone.name for bone in armatureObj.data.bones if \
		bone.parent is None and (bone.geo_cmd != 'SwitchOption' and bone.geo_cmd != 'Ignore')])

	if len(noParentBones) == 0:
		raise PluginError("No non switch option start bone could be found " +\
			'in ' + armatureObj.name + '. Is this the root armature?')
	else:
		return noParentBones
	
	if len(noParentBones) == 1:
		return noParentBones[0]
	elif len(noParentBones) == 0:
		raise PluginError("No non switch option start bone could be found " +\
			'in ' + armatureObj.name + '. Is this the root armature?')
	else:
		raise PluginError("Too many parentless bones found. Make sure your bone hierarchy starts from a single bone, " +\
			"and that any bones not related to a hierarchy have their geolayout command set to \"Ignore\".")

def getDataFromFile(filepath):
	if not os.path.exists(filepath):
		raise PluginError("Path \"" + filepath + '" does not exist.')
	dataFile = open(filepath, 'r', newline = '\n')
	data = dataFile.read()
	dataFile.close()
	return data

def saveDataToFile(filepath, data):
	dataFile = open(filepath, 'w', newline = '\n')
	dataFile.write(data)
	dataFile.close()

def applyBasicTweaks(baseDir):
	enableExtendedRAM(baseDir)
	return

def enableExtendedRAM(baseDir):
	segmentPath = os.path.join(baseDir, 'include/segments.h')

	segmentFile = open(segmentPath, 'r', newline = '\n')
	segmentData = segmentFile.read()
	segmentFile.close()

	matchResult = re.search('#define\s*USE\_EXT\_RAM', segmentData)

	if not matchResult:
		matchResult = re.search('#ifndef\s*USE\_EXT\_RAM', segmentData)
		if matchResult is None:
			raise PluginError("When trying to enable extended RAM, " +\
				"could not find '#ifndef USE_EXT_RAM' in include/segments.h.")
		segmentData = segmentData[:matchResult.start(0)] + \
			'#define USE_EXT_RAM\n' + \
			segmentData[matchResult.start(0):]

		segmentFile = open(segmentPath, 'w', newline = '\n')
		segmentFile.write(segmentData)
		segmentFile.close()

def writeMaterialHeaders(exportDir, matCInclude, matHInclude):
	writeIfNotFound(os.path.join(exportDir, 'src/game/materials.c'), 
		'\n' + matCInclude, '')
	writeIfNotFound(os.path.join(exportDir, 'src/game/materials.h'), 
		'\n' + matHInclude, '#endif')

def writeMaterialFiles(exportDir, assetDir, headerInclude, matHInclude,
	headerDynamic, dynamic_data, geoString, customExport):
	if not customExport:
		writeMaterialBase(exportDir)
	levelMatCPath = os.path.join(assetDir, 'material.inc.c')
	levelMatHPath = os.path.join(assetDir, 'material.inc.h')

	levelMatCFile = open(levelMatCPath, 'w', newline = '\n')
	levelMatCFile.write(dynamic_data)
	levelMatCFile.close()

	headerDynamic = headerInclude + '\n\n' + headerDynamic
	levelMatHFile = open(levelMatHPath, 'w', newline = '\n')
	levelMatHFile.write(headerDynamic)
	levelMatHFile.close()

	return matHInclude + '\n\n' + geoString

def writeMaterialBase(baseDir):
	matHPath = os.path.join(baseDir, 'src/game/materials.h')
	if not os.path.exists(matHPath):
		matHFile = open(matHPath, 'w', newline = '\n')

		# Write material.inc.h
		matHFile.write(
			'#ifndef MATERIALS_H\n' +\
			'#define MATERIALS_H\n\n' + \
			'#endif')

		matHFile.close()
	
	matCPath = os.path.join(baseDir, 'src/game/materials.c')
	if not os.path.exists(matCPath):
		matCFile = open(matCPath, 'w', newline = '\n')
		matCFile.write(
			'#include "types.h"\n' +\
            '#include "rendering_graph_node.h"\n' +\
            '#include "object_fields.h"\n' +\
            '#include "materials.h"')

		# Write global texture load function here
		# Write material.inc.c
		# Write update_materials

		matCFile.close()

def getRGBA16Tuple(color):
	return ((int(color[0] * 0x1F) & 0x1F) << 11) | \
		((int(color[1] * 0x1F) & 0x1F) << 6) | \
		((int(color[2] * 0x1F) & 0x1F) << 1) | \
		(1 if color[3] > 0.5 else 0)

def getIA16Tuple(color):
	intensity = mathutils.Color(color[0:3]).v
	alpha = color[3]
	return (int(intensity * 0xFF) << 8) | int(alpha * 0xFF)

def convertRadiansToS16(value):
	value = math.degrees(value)
	# ??? Why is this negative?
	# TODO: Figure out why this has to be this way
	value = 360 - (value % 360)
	return hex(round(value / 360 * 0xFFFF))

def decompFolderMessage(layout):
	layout.box().label(text = 'This will export to your decomp folder.')

def customExportWarning(layout):
	layout.box().label(text = 'This will not write any headers/dependencies.')

def raisePluginError(operator, exception):
	if bpy.context.scene.fullTraceback:
		operator.report({'ERROR'}, traceback.format_exc())
	else:
		operator.report({'ERROR'}, str(exception))

def highlightWeightErrors(obj, elements, elementType):
	return # Doesn't work currently
	if bpy.context.mode != 'OBJECT':
		bpy.ops.object.mode_set(mode = 'OBJECT')
	bpy.ops.object.select_all(action = "DESELECT")
	obj.select_set(True)
	bpy.context.view_layer.objects.active = obj
	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_all(action = "DESELECT")
	bpy.ops.mesh.select_mode(type = elementType)
	bpy.ops.object.mode_set(mode = 'OBJECT')
	print(elements)
	for element in elements:
		element.select = True

def checkIdentityRotation(obj, rotation, allowYaw):
	rotationDiff = rotation.to_euler()
	if abs(rotationDiff.x) > 0.001 or (not allowYaw and abs(rotationDiff.y) > 0.001) or abs(rotationDiff.z) > 0.001:
		raise PluginError("Box \"" + obj.name + "\" cannot have a non-zero world rotation " + \
			("(except yaw)" if allowYaw else "") + ", currently at (" + \
			str(rotationDiff[0]) + ', ' + str(rotationDiff[1]) + ', ' + str(rotationDiff[2]) + ')')

def setOrigin(target, obj):
	bpy.ops.object.select_all(action = "DESELECT")
	obj.select_set(True)
	bpy.context.view_layer.objects.active = obj
	bpy.ops.object.transform_apply()
	bpy.context.scene.cursor.location = target.location
	bpy.ops.object.origin_set(type = 'ORIGIN_CURSOR')
	bpy.ops.object.select_all(action = "DESELECT")

def checkIfPathExists(filePath):
	if not os.path.exists(filePath):
		raise PluginError(filePath + " does not exist.")

def makeWriteInfoBox(layout):
	writeBox = layout.box()
	writeBox.label(text = 'Along with header edits, this will write to:')
	return writeBox

def writeBoxExportType(writeBox, headerType, name, levelName, levelOption):
	if headerType == 'Actor':
		writeBox.label(text = 'actors/' + toAlnum(name))
	elif headerType == 'Level':
		if levelOption != 'custom':
			levelName = levelOption
		writeBox.label(text = 'levels/' + toAlnum(levelName) + '/' + toAlnum(name))

def getExportDir(customExport, dirPath, headerType, levelName, texDir, dirName):
	# Get correct directory from decomp base, and overwrite texDir
	if not customExport:
		if headerType == 'Actor':
			dirPath = os.path.join(dirPath, 'actors')
			texDir = 'actors/' + dirName
		elif headerType == 'Level':
			dirPath = os.path.join(dirPath, 'levels/' + levelName)
			texDir = 'levels/' + levelName
	
	return dirPath, texDir

def overwriteData(headerRegex, name, value, filePath, writeNewBeforeString, isFunction):
	if os.path.exists(filePath):
		dataFile = open(filePath, 'r')
		data = dataFile.read()
		dataFile.close()

		matchResult = re.search(headerRegex + re.escape(name) + \
			('\s*\((((?!\)).)*)\)\s*\{(((?!\}).)*)\}' if isFunction else \
			'\[\]\s*=\s*\{(((?!;).)*);'), data, re.DOTALL)
		if matchResult:
			data = data[:matchResult.start(0)] + value + data[matchResult.end(0):]
		else:
			if writeNewBeforeString is not None:
				cmdPos = data.find(writeNewBeforeString)
				if cmdPos == -1:
					raise PluginError("Could not find '" + writeNewBeforeString + "'.")
				data = data[:cmdPos] + value + '\n' + data[cmdPos:]
			else:
				data += '\n' + value
		dataFile = open(filePath, 'w', newline='\n')
		dataFile.write(data)
		dataFile.close()
	else:
		raise PluginError(filePath + " does not exist.")

def writeIfNotFound(filePath, stringValue, footer):
	if os.path.exists(filePath):
		fileData = open(filePath, 'r')
		fileData.seek(0)
		stringData = fileData.read()
		fileData.close()
		if stringValue not in stringData:
			if len(footer) > 0:
				footerIndex = stringData.rfind(footer)
				if footerIndex == -1:
					raise PluginError("Footer " + footer + " does not exist.")
				stringData = stringData[:footerIndex] + stringValue + '\n' + stringData[footerIndex:]
			else:
				stringData += stringValue
			fileData = open(filePath, 'w', newline = '\n')
			fileData.write(stringData)
		fileData.close()
	else:
		raise PluginError(filePath + " does not exist.")

def deleteIfFound(filePath, stringValue):
	if os.path.exists(filePath):
		fileData = open(filePath, 'r')
		fileData.seek(0)
		stringData = fileData.read()
		fileData.close()
		if stringValue in stringData:
			stringData = stringData.replace(stringValue, '')
			fileData = open(filePath, 'w', newline = '\n')
			fileData.write(stringData)
		fileData.close()

def duplicateHierarchy(obj, ignoreAttr, includeEmpties, areaIndex):
	# Duplicate objects to apply scale / modifiers / linked data
	bpy.ops.object.select_all(action = 'DESELECT')
	selectMeshChildrenOnly(obj, None, includeEmpties, areaIndex)
	obj.select_set(True)
	bpy.context.view_layer.objects.active = obj
	bpy.ops.object.duplicate()
	try:
		tempObj = bpy.context.view_layer.objects.active
		allObjs = bpy.context.selected_objects
		bpy.ops.object.make_single_user(obdata = True)
		bpy.ops.object.transform_apply(location = False, 
			rotation = True, scale = True, properties =  False)
		for selectedObj in allObjs:
			bpy.ops.object.select_all(action = 'DESELECT')
			selectedObj.select_set(True)
			bpy.context.view_layer.objects.active = selectedObj
			for modifier in selectedObj.modifiers:
				bpy.ops.object.modifier_apply(modifier=modifier.name)
		for selectedObj in allObjs:
			if ignoreAttr is not None and getattr(selectedObj, ignoreAttr):
				for child in selectedObj.children:
					bpy.ops.object.select_all(action = 'DESELECT')
					child.select_set(True)
					bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
					selectedObj.parent.select_set(True)
					bpy.ops.object.parent_set(keep_transform = True)
				selectedObj.parent = None
		return tempObj, allObjs
	except Exception as e:
		cleanupDuplicatedObjects(allObjs)
		obj.select_set(True)
		bpy.context.view_layer.objects.active = obj
		raise Exception(str(e))

def selectMeshChildrenOnly(obj, ignoreAttr, includeEmpties, areaIndex):
	checkArea = areaIndex is not None and obj.data is None
	if checkArea and obj.sm64_obj_type == 'Area Root' and obj.areaIndex != areaIndex:
		return
	ignoreObj = ignoreAttr is not None and getattr(obj, ignoreAttr)
	isMesh = isinstance(obj.data, bpy.types.Mesh)
	isEmpty = (obj.data is None) and includeEmpties and \
		(obj.sm64_obj_type == 'Level Root' or \
		obj.sm64_obj_type == 'Area Root' or \
		obj.sm64_obj_type == 'None' or \
		obj.sm64_obj_type == 'Switch')
	if (isMesh or isEmpty) and not ignoreObj:
		obj.select_set(True)
		obj.original_name = obj.name
	for child in obj.children:
		if checkArea and obj.sm64_obj_type == 'Level Root':
			if not (child.data is None and child.sm64_obj_type == 'Area Root'):
				continue
		selectMeshChildrenOnly(child, ignoreAttr, includeEmpties, areaIndex)

def cleanupDuplicatedObjects(selected_objects):
	meshData = []
	for selectedObj in selected_objects:
		if selectedObj.data is not None:
			meshData.append(selectedObj.data)
	for selectedObj in selected_objects:
		bpy.data.objects.remove(selectedObj)
	for mesh in meshData:
		bpy.data.meshes.remove(mesh)

def combineObjects(obj, includeChildren, ignoreAttr, areaIndex):
	obj.original_name = obj.name

	# Duplicate objects to apply scale / modifiers / linked data
	bpy.ops.object.select_all(action = 'DESELECT')
	if includeChildren:
		selectMeshChildrenOnly(obj, ignoreAttr, False, areaIndex)
	else:
		obj.select_set(True)
	if len(bpy.context.selected_objects) == 0:
		return None, []
	bpy.ops.object.duplicate()
	joinedObj = None
	try:
		# duplicate obj and apply modifiers / make single user
		allObjs = bpy.context.selected_objects
		bpy.ops.object.make_single_user(obdata = True)
		bpy.ops.object.transform_apply(location = False, 
			rotation = True, scale = True, properties =  False)
		for selectedObj in allObjs:
			bpy.ops.object.select_all(action = 'DESELECT')
			selectedObj.select_set(True)
			for modifier in selectedObj.modifiers:
				try:
					bpy.ops.object.modifier_apply(modifier=modifier.name)
				except RuntimeError as error:
					print(str(error))
					
		bpy.ops.object.select_all(action = 'DESELECT')
		
		# Joining causes orphan data, so we remove it manually.
		meshList = []
		for selectedObj in allObjs:
			selectedObj.select_set(True)
			meshList.append(selectedObj.data)
		
		joinedObj = bpy.context.selected_objects[0]
		bpy.context.view_layer.objects.active = joinedObj
		joinedObj.select_set(True)
		meshList.remove(joinedObj.data)
		bpy.ops.object.join()
		setOrigin(obj, joinedObj)

		bpy.ops.object.select_all(action = 'DESELECT')
		bpy.context.view_layer.objects.active = joinedObj
		joinedObj.select_set(True)

		# Need to clear parent transform in order to correctly apply transform.
		bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
		bpy.ops.object.transform_apply(location = False, 
			rotation = True, scale = True, properties =  False)
		bpy.context.view_layer.objects.active = joinedObj
		joinedObj.select_set(True)
		bpy.ops.object.transform_apply(location = False, 
			rotation = True, scale = True, properties =  False)

	except Exception as e:
		cleanupDuplicatedObjects(allObjs)
		obj.select_set(True)
		bpy.context.view_layer.objects.active = obj
		raise Exception(str(e))

	return joinedObj, meshList

def cleanupCombineObj(tempObj, meshList):
	for mesh in meshList:
		bpy.data.meshes.remove(mesh)
	cleanupDuplicatedObjects([tempObj])
	#obj.select_set(True)
	#bpy.context.view_layer.objects.active = obj

def writeInsertableFile(filepath, dataType, address_ptrs, startPtr, data):
	address = 0
	openfile = open(filepath, 'wb')

	# 0-4 - Data Type
	openfile.write(dataType.to_bytes(4, 'big'))
	address += 4

	# 4-8 - Data Size
	openfile.seek(address)
	openfile.write(len(data).to_bytes(4, 'big'))
	address += 4

	# 8-12 Start Address
	openfile.seek(address)
	openfile.write(startPtr.to_bytes(4, 'big'))
	address += 4

	# 12-16 - Number of pointer addresses
	openfile.seek(address)
	openfile.write(len(address_ptrs).to_bytes(4, 'big'))
	address += 4

	# 16-? - Pointer address list
	for i in range(len(address_ptrs)):
		openfile.seek(address)
		openfile.write(address_ptrs[i].to_bytes(4, 'big'))
		address += 4

	openfile.seek(address)
	openfile.write(data)	
	openfile.close()

def colorTo16bitRGBA(color):
	r = int(round(color[0] * 31))
	g = int(round(color[1] * 31))
	b = int(round(color[2] * 31))
	a = 1 if color[3] > 0.5 else 0

	return (r << 11) | (g << 6) | (b << 1) | a

# On 2.83/2.91 the rotate operator rotates in the opposite direction (???)
def getDirectionGivenAppVersion():
	if bpy.app.version[1] == 83 or bpy.app.version[1] == 91:
		return -1
	else:
		return 1

def applyRotation(objList, angle, axis):
	bpy.context.scene.tool_settings.use_transform_data_origin = False
	bpy.context.scene.tool_settings.use_transform_pivot_point_align = False
	bpy.context.scene.tool_settings.use_transform_skip_children = False

	bpy.ops.object.select_all(action = "DESELECT")
	for obj in objList:
		obj.select_set(True)
	bpy.context.view_layer.objects.active = objList[0]

	direction = getDirectionGivenAppVersion()

	bpy.ops.transform.rotate(value = direction * angle, orient_axis = axis, orient_type='GLOBAL')
	bpy.ops.object.transform_apply(location = False, 
		rotation = True, scale = True, properties =  False)

def doRotation(angle, axis):
	direction = getDirectionGivenAppVersion()
	bpy.ops.transform.rotate(value = direction * angle, orient_axis = axis, orient_type='GLOBAL')

def getAddressFromRAMAddress(RAMAddress):
	addr = RAMAddress - 0x80000000
	if addr < 0:
		raise PluginError("Invalid RAM address.")
	return addr

def getObjectQuaternion(obj):
	if obj.rotation_mode == 'QUATERNION':
		rotation = mathutils.Quaternion(obj.rotation_quaternion)
	elif obj.rotation_mode == 'AXIS_ANGLE':
		rotation = mathutils.Quaternion(obj.rotation_axis_angle)
	else:
		rotation = mathutils.Euler(
			obj.rotation_euler, obj.rotation_mode).to_quaternion()
	return rotation

def tempName(name):
   letters = string.digits
   return name + '_temp' + "".join(random.choice(letters) for i in range(10))

def prop_split(layout, data, field, name):
	split = layout.split(factor = 0.5)
	split.label(text = name)
	split.prop(data, field, text = '')

def toAlnum(name):
	if name is None or name == '':
		return None
	for i in range(len(name)):
		if not name[i].isalnum():
			name = name[:i] + '_' + name[i+1:]
	if name[0].isdigit():
		name = '_' + name
	return name

def get64bitAlignedAddr(address):
	endNibble = hex(address)[-1]
	if endNibble != '0' and endNibble != '8':
		address = ceil(address / 8) * 8
	return address

def getNameFromPath(path, removeExtension = False):
	if path[:2] == '//':
		path = path[2:]
	name = os.path.basename(path)
	if removeExtension:
		name = os.path.splitext(name)[0]
	return toAlnum(name)
	
def gammaCorrect(color):
	return [
		gammaCorrectValue(color[0]), 
		gammaCorrectValue(color[1]), 
		gammaCorrectValue(color[2])]

def gammaCorrectValue(u):
	if u < 0.0031308:
		y = u * 12.92
	else:
		y = 1.055 * pow(u, (1/2.4)) - 0.055
	
	return min(max(y, 0), 1)

def gammaInverse(color):
	return [
		gammaInverseValue(color[0]), 
		gammaInverseValue(color[1]), 
		gammaInverseValue(color[2])]

def gammaInverseValue(u):
	if u < 0.04045:
		y = u / 12.92
	else:
		y = ((u + 0.055) / 1.055) ** 2.4
	
	return min(max(y, 0), 1)

def printBlenderMessage(msgSet, message, blenderOp):
	if blenderOp is not None:
		blenderOp.report(msgSet, message)
	else:
		print(message)

def bytesToInt(value):
	return int.from_bytes(value, 'big')

def bytesToHex(value, byteSize = 4):
	return format(bytesToInt(value), '#0' + str(byteSize * 2 + 2) + 'x')

def bytesToHexClean(value, byteSize = 4):
	return format(bytesToInt(value), '0' + str(byteSize * 2) + 'x')

def intToHex(value, byteSize = 4):
	return format(value, '#0' + str(byteSize * 2 + 2) + 'x')

def intToBytes(value, byteSize):
	return bytes.fromhex(intToHex(value, byteSize)[2:])

# byte input
# returns an integer, usually used for file seeking positions
def decodeSegmentedAddr(address, segmentData):
	#print(bytesAsHex(address))
	if address[0] not in segmentData:
		raise PluginError("Segment " + str(address[0]) + ' not found in segment list.')
	segmentStart = segmentData[address[0]][0]
	return segmentStart + bytesToInt(address[1:4])

#int input
# returns bytes, usually used for writing new segmented addresses
def encodeSegmentedAddr(address, segmentData):
	segment = getSegment(address, segmentData)
	segmentStart = segmentData[segment][0]

	segmentedAddr = address - segmentStart
	return intToBytes(segment, 1) + intToBytes(segmentedAddr, 3)

def getSegment(address, segmentData):
	for segment, interval in segmentData.items():
		if address in range(*interval):
			return segment

	raise PluginError("Address " + hex(address) + \
		" is not found in any of the provided segments.")

# Position
def readVectorFromShorts(command, offset):
	return [readFloatFromShort(command, valueOffset) for valueOffset
		in range(offset, offset + 6, 2)]

def readFloatFromShort(command, offset):
	return int.from_bytes(command[offset: offset + 2], 
		'big', signed = True) / bpy.context.scene.blenderToSM64Scale

def writeVectorToShorts(command, offset, values):
	for i in range(3):
		valueOffset = offset + i * 2
		writeFloatToShort(command, valueOffset, values[i])

def writeFloatToShort(command, offset, value):
	command[offset : offset + 2] = \
		int(round(value * bpy.context.scene.blenderToSM64Scale)).to_bytes(
		2, 'big', signed = True)

def convertFloatToShort(value):
	return int(round((value * bpy.context.scene.blenderToSM64Scale)))

def convertEulerFloatToShort(value):
	return int(round(degrees(value)))

# Rotation

# Rotation is stored as a short.
# Zero rotation starts at Z+ on an XZ plane and goes counterclockwise.
# 2**16 - 1 is the last value before looping around again.
def readEulerVectorFromShorts(command, offset):
	return [readEulerFloatFromShort(command, valueOffset) for valueOffset
		in range(offset, offset + 6, 2)]

def readEulerFloatFromShort(command, offset):
	return radians(int.from_bytes(command[offset: offset + 2], 
		'big', signed = True))

def writeEulerVectorToShorts(command, offset, values):
	for i in range(3):
		valueOffset = offset + i * 2
		writeEulerFloatToShort(command, valueOffset, values[i])

def writeEulerFloatToShort(command, offset, value):
	command[offset : offset + 2] = int(round(degrees(value))).to_bytes(
		2, 'big', signed = True)

# convert 32 bit (8888) to 16 bit (5551) color
def convert32to16bitRGBA(oldPixel):
	if oldPixel[3] > 127:
		alpha = 1
	else:
		alpha = 0
	newPixel = 	(oldPixel[0] >> 3) << 11 |\
				(oldPixel[1] >> 3) << 6  |\
				(oldPixel[2] >> 3) << 1  |\
				alpha
	return newPixel.to_bytes(2, 'big')

# convert normalized RGB values to bytes (0-255)
def convertRGB(normalizedRGB):
	return bytearray([
		int(normalizedRGB[0] * 255),
		int(normalizedRGB[1] * 255),
		int(normalizedRGB[2] * 255)
		])
# convert normalized RGB values to bytes (0-255)
def convertRGBA(normalizedRGBA):
	return bytearray([
		int(normalizedRGBA[0] * 255),
		int(normalizedRGBA[1] * 255),
		int(normalizedRGBA[2] * 255),
		int(normalizedRGBA[3] * 255)
		])

def vector3ComponentMultiply(a, b):
	return mathutils.Vector(
		(a.x * b.x, a.y * b.y, a.z * b.z)
	)

# Position values are signed shorts.
def convertPosition(position):
	positionShorts = [int(floatValue) for floatValue in position]
	F3DPosition = bytearray(0)
	for shortData in [shortValue.to_bytes(2, 'big', signed=True) for shortValue in positionShorts]:
		F3DPosition.extend(shortData)
	return F3DPosition

# UVs in F3D are a fixed point short: s10.5 (hence the 2**5)
# fixed point is NOT exponent+mantissa, it is integer+fraction
def convertUV(normalizedUVs, textureWidth, textureHeight):
	#print(str(normalizedUVs[0]) + " - " + str(normalizedUVs[1]))
	F3DUVs = convertFloatToFixed16Bytes(normalizedUVs[0] * textureWidth) +\
			 convertFloatToFixed16Bytes(normalizedUVs[1] * textureHeight)
	return F3DUVs

def convertFloatToFixed16Bytes(value):
	value *= 2**5
	value = min(max(value, -2**15), 2**15 - 1)
	
	return int(round(value)).to_bytes(2, 'big', signed = True)

def convertFloatToFixed16(value):
	return int(round(value * (2**5)))

	# We want support for large textures with 32 bit UVs
	#value *= 2**5
	#value = min(max(value, -2**15), 2**15 - 1)
	#return int.from_bytes(
	#	int(round(value)).to_bytes(2, 'big', signed = True), 'big')


# Normal values are signed bytes (-128 to 127)
# Normalized magnitude = 127
def convertNormal(normal):
	F3DNormal = bytearray(0)
	for axis in normal:
		F3DNormal.extend(int(axis * 127).to_bytes(1, 'big', signed=True))
	return F3DNormal

def byteMask(data, offset, amount):
	return bitMask(data, offset * 8, amount * 8)
def bitMask(data, offset, amount):
	return (~(-1 << amount) << offset & data) >> offset

def read16bitRGBA(data):
	r = bitMask(data, 11, 5) / ((2**5) - 1)
	g = bitMask(data,  6, 5) / ((2**5) - 1)
	b = bitMask(data,  1, 5) / ((2**5) - 1)
	a = bitMask(data,  0, 1) / ((2**1) - 1)

	return [r,g,b,a]