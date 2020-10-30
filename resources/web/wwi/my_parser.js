class MyParser {
  constructor() {
    this.Nodes = [];
  }

  parse(text){
    console.log('X3D: Parsing');

    let xml = null;
    if (window.DOMParser) {
      let parser = new DOMParser();
      xml = parser.parseFromString(text, 'text/xml');
    } else { // Internet Explorer
      xml = new ActiveXObject('Microsoft.XMLDOM');
      xml.async = false;
      xml.loadXML(text);
    }

    let scene = xml.getElementsByTagName('Scene')[0];
    console.log(scene);
    if (scene === undefined) {
      console.error("Scene not found");
    } else {
      this.parseNode(scene);
    }

    console.log("File Parsed");

    //Render a first time after beeing parsed
    //TODO move after parse is called.
    _wr_scene_render(_wr_scene_get_instance(), null, true);
  }

  parseNode(node) {
    if(node.tagName === 'Scene') {
      let id = getNodeAttribute(node, 'id');
      new WbScene(id);
      this.parseChildren(node);
    } else if (node.tagName === 'WorldInfo') {
      this.parseWorldInfo(node);
    } else if (node.tagName === 'Viewpoint') {
      this.parseViewpoint(node);
    } else if (node.tagName === 'Shape') {
      this.parseShape(node);
    } else {
      console.log(node.tagName);
      console.error("The parser doesn't support this type of node");
    }
  }

  parseChildren(node, currentObject) {
    for (let i = 0; i < node.childNodes.length; i++) {
      let child = node.childNodes[i];
      if (typeof child.tagName !== 'undefined'){
        this.parseNode(child);
      }

    }
  }

  parseWorldInfo(node){
    console.log("Un WorldInfo");
  }

  parseViewpoint(node){
    let id = getNodeAttribute(node, 'id');
    let orientation = convertStringToQuaternion(getNodeAttribute(node, 'orientation', '0 1 0 0'));
    let position = convertStringToVec3(getNodeAttribute(node, 'position', '0 0 10'));
    let exposure = parseFloat(getNodeAttribute(node, 'exposure', '1.0'));
    let bloomThreshold = parseFloat(getNodeAttribute(node, 'bloomThreshold'));
    let far = parseFloat(getNodeAttribute(node, 'zFar', '2000'));
    let zNear = parseFloat(getNodeAttribute(node, 'zNear', '0.1'));
    let followsmoothness = parseFloat(getNodeAttribute(node, 'followsmoothness'));

    let viewpoint = new WbViewpoint(id, orientation, position, exposure, bloomThreshold, zNear, far, followsmoothness);
  }

  parseShape(node){
    let id = getNodeAttribute(node, 'id');
    let castShadows = getNodeAttribute(node, 'castShadows', 'false').toLowerCase() === 'true';

    let shape = new WbShape(id, castShadows);

    let geometry = this.parseGeometry(node.childNodes[0]);
    shape.geometry = geometry;
    shape.createWrenObjects();
  }

  parseGeometry(node){
    let geometry;
    if(node.tagName === 'Box') {
      geometry = this.parseBox(node);
    }else if (node.tagName === 'Sphere'){
      geometry = this.parseSphere(node);
    } else {
      console.log("Not a recognized geometry");
      geometry = undefined
    }
    return geometry;
  }

  parseBox(node) {
    let id = getNodeAttribute(node, 'id');
    let size = convertStringToVec3(getNodeAttribute(node, 'size', '2 2 2'));

    return new WbBox(id, size);
  }

  parseSphere(node){
    let id = getNodeAttribute(node, 'id');
    let radius = parseFloat(getNodeAttribute(node, 'radius', '1'));
    let ico = getNodeAttribute(node, 'ico', 'false').toLowerCase() === 'true'
    let subdivision = parseInt(getNodeAttribute(node, 'subdivision', '1,1'));

    return new WbSphere(id, radius, ico, subdivision);
  }
}

function getNodeAttribute(node, attributeName, defaultValue) {
  console.assert(node && node.attributes);
  if (attributeName in node.attributes)
    return node.attributes.getNamedItem(attributeName).value;
  return defaultValue;
}

function convertStringToVec3(s) {
  s = s.split(/\s/);
  let v = new glm.vec3(parseFloat(s[0]), parseFloat(s[1]), parseFloat(s[2]));
  return v;
}

function convertStringToQuaternion(s) {
  let pos = s.split(/\s/);
  let q = new glm.vec4(parseFloat(pos[0]), parseFloat(pos[1]), parseFloat(pos[2]), parseFloat(pos[3]));
  return q;
}
